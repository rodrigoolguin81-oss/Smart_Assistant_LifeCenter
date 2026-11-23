"""SPEC-004 E1 — the project's own agenda in Neon (specs/007-agenda; G1–G23, G10b).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main` (conftest refuses it).

- Fake Telegram ids `900101…` only. Every appointment of those ids, and every closure marked
  TEST_CLOSURE, is removed before and after each test.
- Dates are computed from today, so results do not depend on the day the tests run and no
  synthetic appointment falls into the 30-day purge by accident. The tests call the internal
  `_at` functions with a fixed `p_now`; the public functions are checked separately.
- The consent key is never selected or printed.

Interface under test (plan Step 2):
  agenda_free_slots(type, from, limit DEFAULT 3)          -> (result, starts_at, ends_at, professional)
  agenda_free_slots_at(type, from, limit, now)            -> same
  agenda_book(type, start, from_id)                       -> (result, reason, appointment_id,
  agenda_book_at(type, start, from_id, now)                   starts_at, ends_at, professional, room)
  agenda_subject(from_id)                                 -> 64-hex HMAC('agenda:'||id, consent key)
"""

import re
import threading
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest

from app.infra.schema import apply_schema

MADRID = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parents[2]
HOR_001 = ROOT / "kb" / "horario-clinica.md"
FAKE_IDS = [str(900101 + i) for i in range(60)]
TEST_CLOSURE = "TEST-SPEC-004"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

DENTISTS = {"odontologa_1", "odontologo_2"}
HYGIENIST = "higienista"
ROOMS = {"gabinete_1", "gabinete_2", "gabinete_3"}


# --- Dates (computed from today; Monday-based week, Madrid local times) ---


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def _last_sunday(year: int, month: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def at(day: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(day, time(h, m), MADRID)


def local(dt: datetime) -> str:
    return dt.astimezone(MADRID).strftime("%Y-%m-%d %H:%M")


MON = _next_monday(date.today() + timedelta(days=14))  # a Monday at least two weeks ahead
if MON.month == 8:  # keep the main tests out of August (reduced hours, tested apart)
    MON = _next_monday(date(MON.year, 9, 1))
TUE, SAT, SUN = MON + timedelta(days=1), MON - timedelta(days=2), MON - timedelta(days=1)
NOW = at(MON - timedelta(days=3), "07:00")  # the Friday before, 07:00 Madrid


def _dst_weeks() -> list[tuple[str, date]]:
    """The next Madrid DST changes (last Sunday of March and of October) still ahead."""
    out, year = [], date.today().year
    while len(out) < 2:
        for month in (3, 10):
            sunday = _last_sunday(year, month)
            if sunday > date.today() + timedelta(days=4) and len(out) < 2:
                out.append(("march" if month == 3 else "october", sunday))
        year += 1
    return out


# --- Fixtures and helpers ---


def _agenda_exists(conn) -> bool:
    return conn.execute("SELECT to_regclass('public.agenda_appointments') IS NOT NULL").fetchone()[0]


def _cleanup(conn) -> None:
    if not _agenda_exists(conn):
        return
    conn.execute(
        "DELETE FROM agenda_appointments WHERE subject IN (SELECT agenda_subject(x) FROM unnest(%s::text[]) x)",
        (FAKE_IDS,),
    )
    conn.execute("DELETE FROM agenda_closures WHERE reason = %s", (TEST_CLOSURE,))


@pytest.fixture
def db(test_db):
    _cleanup(test_db)
    yield test_db
    _cleanup(test_db)


def free_slots(conn, type_code, start, limit=3, now=NOW):
    return conn.execute(
        "SELECT result, starts_at, ends_at, professional FROM agenda_free_slots_at(%s, %s, %s, %s)",
        (type_code, start, limit, now),
    ).fetchall()


def book(conn, type_code, start, from_id, now=NOW):
    return conn.execute(
        "SELECT result, reason, appointment_id, starts_at, ends_at, professional, room"
        " FROM agenda_book_at(%s, %s, %s, %s)",
        (type_code, start, from_id, now),
    ).fetchone()


def insert_raw(conn, from_id, type_code, start, end, professional, room, status="booked"):
    conn.execute(
        "INSERT INTO agenda_appointments (subject, type_code, starts_at, ends_at, professional, room, status, channel)"
        " VALUES (agenda_subject(%s), %s, %s, %s, %s, %s, %s, 'telegram')",
        (from_id, type_code, start, end, professional, room, status),
    )


def count_for(conn, from_id) -> int:
    return conn.execute(
        "SELECT count(*) FROM agenda_appointments WHERE subject = agenda_subject(%s)", (from_id,)
    ).fetchone()[0]


CONNECTION_ERRORS = ("OperationalError", "BrokenBarrierError", "ConnectionTimeout", "sin_resultado")


def run_concurrently(url, calls):
    """Run agenda_book_at calls at the same moment, one connection per call, behind a barrier.

    Every slot of the result is a tuple, so an assertion can always print the whole list:
    - a failed connection breaks the barrier (timeout), so the other threads record
      BrokenBarrierError instead of waiting forever;
    - a thread that did not finish is reported as ("sin_resultado", ...).
    """
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(i, args):
        try:
            with psycopg.connect(url, autocommit=True, connect_timeout=30) as conn:
                barrier.wait(timeout=60)
                results[i] = conn.execute(
                    "SELECT result, professional, room FROM agenda_book_at(%s, %s, %s, %s)", args
                ).fetchone()
        except Exception as exc:  # recorded, so the test reports it instead of hanging
            barrier.abort()
            results[i] = ("exception", type(exc).__name__, str(exc))

    threads = [threading.Thread(target=worker, args=(i, a)) for i, a in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=90)
    return [r if r is not None else ("sin_resultado", "hilo sin terminar", "") for r in results]


def connection_failed(results) -> bool:
    """True when some call never reached the database because of the connection or the barrier."""
    return any(r[0] == "sin_resultado" or (r[0] == "exception" and r[1] in CONNECTION_ERRORS) for r in results)


# === G1–G3: configuration ===


def test_g1_g2_configuration_tables_hold_the_example_staff_rooms_and_types(db):
    pros = db.execute("SELECT code, role, ejemplo FROM agenda_professionals ORDER BY code").fetchall()
    assert pros == [("higienista", "hygienist", True), ("odontologa_1", "dentist", True), ("odontologo_2", "dentist", True)]
    rooms = db.execute("SELECT code, ejemplo FROM agenda_rooms ORDER BY code").fetchall()
    assert rooms == [("gabinete_1", True), ("gabinete_2", True), ("gabinete_3", True)]
    types = db.execute(
        "SELECT code, extract(epoch FROM duration)::int / 60, role, bookable_by_bot, ejemplo FROM agenda_types ORDER BY code"
    ).fetchall()
    assert types == [
        ("blanqueamiento", 90, "dentist", False, True),
        ("limpieza", 45, "hygienist", True, True),
        ("primera_visita", 30, "dentist", True, True),
        ("revision", 30, "dentist", True, True),
        ("tratamiento_largo", None, "dentist", False, True),
    ]


def test_g2_settings_hold_the_example_rules(db):
    row = db.execute(
        "SELECT slot_minutes, min_lead, horizon, max_future_per_subject, ejemplo FROM agenda_settings"
    ).fetchall()
    assert row == [(15, timedelta(hours=2), timedelta(days=30), 1, True)]


def test_g2_no_closures_besides_tests(db):
    assert db.execute("SELECT count(*) FROM agenda_closures").fetchone()[0] == 0


def test_g3_a_type_can_only_be_given_to_a_professional_of_its_role(db):
    with pytest.raises((psycopg.errors.RaiseException, psycopg.errors.IntegrityError)):
        insert_raw(db, FAKE_IDS[0], "limpieza", at(MON, "09:00"), at(MON, "09:45"), "odontologa_1", "gabinete_1")


def test_g3_status_and_role_values_are_constrained(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_raw(db, FAKE_IDS[0], "revision", at(MON, "09:00"), at(MON, "09:30"), "odontologa_1", "gabinete_1", status="pending")


# === G4: opening hours equal HOR-001 ===


def _hor001_blocks() -> set[tuple[int, str, str, int]]:
    """(ISO weekday, start, end, month) for every month, parsed from kb/horario-clinica.md."""
    text = HOR_001.read_text(encoding="utf-8")
    week = re.search(
        r"de lunes a viernes de (\d{1,2}:\d{2}) a (\d{1,2}:\d{2}) y de (\d{1,2}:\d{2}) a (\d{1,2}:\d{2})", text
    )
    sat = re.search(r"Los sábados la clínica abre de (\d{1,2}:\d{2}) a (\d{1,2}:\d{2})", text)
    closed = re.search(r"Los domingos y festivos permanece cerrada", text)
    august = re.search(r"Durante el mes de agosto la clínica abre solo por las mañanas, de (\d{1,2}:\d{2}) a (\d{1,2}:\d{2})", text)
    if not (week and sat and closed and august):
        pytest.fail("kb/horario-clinica.md changed its wording: update the parser of this test (G4)")
    norm = lambda s: f"{int(s.split(':')[0]):02d}:{s.split(':')[1]}"
    m1, m2, a1, a2 = map(norm, week.groups())
    s1, s2 = map(norm, sat.groups())
    g1, g2 = map(norm, august.groups())
    blocks = set()
    for month in range(1, 13):
        for wd in range(1, 6):
            if month == 8:
                blocks.add((wd, g1, g2, month))  # August: mornings only (clarifications, proposal)
            else:
                blocks.add((wd, m1, m2, month))
                blocks.add((wd, a1, a2, month))
        blocks.add((6, s1, s2, month))  # Saturday morning unchanged in August (proposal)
    return blocks


def test_g4_opening_blocks_equal_hor001(db):
    rows = db.execute(
        "SELECT weekday, to_char(start_time, 'HH24:MI'), to_char(end_time, 'HH24:MI'), m"
        " FROM agenda_hours, unnest(months) m"
    ).fetchall()
    assert set(rows) == _hor001_blocks()


def test_g4_august_has_no_afternoon_slots(db):
    aug_mon = _next_monday(date(MON.year if MON.month < 8 else MON.year + 1, 8, 1))
    slots = free_slots(db, "revision", at(aug_mon, "00:00"), limit=3, now=at(aug_mon - timedelta(days=3), "07:00"))
    assert [local(s[1]) for s in slots][:2] == [
        local(at(aug_mon, "09:00")),
        local(at(aug_mon + timedelta(days=1), "09:00")),
    ]


# === G5–G8: free slots ===


def test_g5_g6_limpieza_offers_three_earliest_slots_one_per_block_for_the_hygienist(db):
    slots = free_slots(db, "limpieza", at(MON, "00:00"))
    assert [(r, local(s), local(e), p) for r, s, e, p in slots] == [
        ("free", local(at(MON, "09:00")), local(at(MON, "09:45")), HYGIENIST),
        ("free", local(at(MON, "16:00")), local(at(MON, "16:45")), HYGIENIST),
        ("free", local(at(TUE, "09:00")), local(at(TUE, "09:45")), HYGIENIST),
    ]


def test_g5_limit_is_respected(db):
    assert len(free_slots(db, "revision", at(MON, "00:00"), limit=5)) == 5
    assert len(free_slots(db, "revision", at(MON, "00:00"), limit=1)) == 1


def test_g5_a_busy_hygienist_moves_limpieza_but_not_revision(db):
    # The hygienist is busy 9:00–13:30: a 45-minute limpieza no longer fits that morning
    # (13:30 would cross 14:00), while a dentist is still free at 9:00.
    insert_raw(db, FAKE_IDS[0], "limpieza", at(MON, "09:00"), at(MON, "13:30"), HYGIENIST, "gabinete_3")
    limpieza = free_slots(db, "limpieza", at(MON, "00:00"), limit=1)
    assert [(local(s), p) for _, s, _, p in limpieza] == [(local(at(MON, "16:00")), HYGIENIST)]
    revision = free_slots(db, "revision", at(MON, "00:00"), limit=1)
    assert [local(s) for _, s, _, _ in revision] == [local(at(MON, "09:00"))]
    assert revision[0][3] in DENTISTS


def test_g6_slots_are_on_the_grid_inside_blocks_and_inside_the_window(db):
    slots = free_slots(db, "limpieza", at(MON, "00:00"), limit=40)
    assert slots
    for _, s, e, _ in slots:
        ls, le = s.astimezone(MADRID), e.astimezone(MADRID)
        assert ls.minute % 15 == 0 and ls.second == 0
        assert ls.date() == le.date() and ls.isoweekday() != 7
        assert (time(9) <= ls.time() and le.time() <= time(14)) or (time(16) <= ls.time() and le.time() <= time(20)) \
            or (ls.isoweekday() == 6 and time(10) <= ls.time() and le.time() <= time(14))
        assert NOW + timedelta(hours=2) <= s <= NOW + timedelta(days=30)


def test_g6_no_slot_less_than_two_hours_ahead(db):
    now = at(MON, "08:00")
    first = free_slots(db, "revision", at(MON, "00:00"), limit=1, now=now)
    assert [local(s) for _, s, _, _ in first] == [local(at(MON, "10:00"))]


def test_g6_no_slot_beyond_thirty_days(db):
    assert free_slots(db, "revision", NOW + timedelta(days=30, hours=1)) == []
    last = free_slots(db, "revision", NOW + timedelta(days=29), limit=40)
    assert all(s <= NOW + timedelta(days=30) for _, s, _, _ in last)


def test_g6_no_slot_on_sunday(db):
    first = free_slots(db, "revision", at(SAT, "14:00"), limit=1)
    assert [local(s) for _, s, _, _ in first] == [local(at(MON, "09:00"))]


def test_g6_no_slot_on_a_closure(db):
    db.execute("INSERT INTO agenda_closures (day, reason) VALUES (%s, %s)", (MON, TEST_CLOSURE))
    first = free_slots(db, "revision", at(MON, "00:00"), limit=1)
    assert [local(s) for _, s, _, _ in first] == [local(at(TUE, "09:00"))]


def test_g7_request_only_types_offer_no_slots(db):
    for t in ("blanqueamiento", "tratamiento_largo"):
        assert free_slots(db, t, at(MON, "00:00")) == [("request_only", None, None, None)]


def test_g8_unknown_type_is_an_error(db):
    with pytest.raises(psycopg.errors.RaiseException):
        free_slots(db, "no_existe", at(MON, "00:00"))


# === G9–G11, G10b: booking primitive ===


def test_g9_booking_creates_one_appointment_with_a_professional_of_the_role(db):
    result, reason, appt_id, s, e, pro, room = book(db, "limpieza", at(MON, "09:00"), FAKE_IDS[0])
    assert (result, reason) == ("booked", None)
    assert appt_id is not None and pro == HYGIENIST and room in ROOMS
    assert (local(s), local(e)) == (local(at(MON, "09:00")), local(at(MON, "09:45")))
    assert count_for(db, FAKE_IDS[0]) == 1
    rev = book(db, "revision", at(MON, "09:00"), FAKE_IDS[1])
    assert rev[0] == "booked" and rev[5] in DENTISTS


@pytest.mark.parametrize(
    "type_code,start,reason",
    [
        ("revision", lambda: at(MON, "08:45"), "outside_hours"),
        ("revision", lambda: at(MON, "20:00"), "outside_hours"),
        ("revision", lambda: at(SUN, "10:00"), "closed"),
        ("limpieza", lambda: at(MON, "13:30"), "outside_hours"),  # crosses the break
        ("limpieza", lambda: at(MON, "19:30"), "outside_hours"),  # crosses the closing time
        ("revision", lambda: at(MON, "09:10"), "not_on_grid"),
        ("revision", lambda: NOW + timedelta(hours=1), "too_soon"),
        ("revision", lambda: at(MON + timedelta(days=28), "10:00"), "too_far"),
        ("blanqueamiento", lambda: at(MON, "09:00"), "request_only"),
        ("no_existe", lambda: at(MON, "09:00"), "unknown_type"),
    ],
)
def test_g10_booking_applies_the_slot_rules(db, type_code, start, reason):
    if reason == "too_soon":
        start_dt, now = at(MON, "09:00"), at(MON, "08:00")
    else:
        start_dt, now = start(), NOW
    result = book(db, type_code, start_dt, FAKE_IDS[0], now=now)
    assert (result[0], result[1]) == ("invalid", reason)
    assert count_for(db, FAKE_IDS[0]) == 0


def test_g10_booking_on_a_closure_is_invalid(db):
    db.execute("INSERT INTO agenda_closures (day, reason) VALUES (%s, %s)", (MON, TEST_CLOSURE))
    assert book(db, "revision", at(MON, "10:00"), FAKE_IDS[0])[:2] == ("invalid", "closed")
    assert count_for(db, FAKE_IDS[0]) == 0


def test_g10b_one_future_appointment_per_subject(db):
    assert book(db, "revision", at(MON, "09:00"), FAKE_IDS[0])[0] == "booked"
    again = book(db, "limpieza", at(TUE, "16:00"), FAKE_IDS[0])
    assert again[0] == "limit"
    assert count_for(db, FAKE_IDS[0]) == 1


def test_g10b_the_limit_holds_under_concurrency(db, test_database_url):
    results = run_concurrently(
        test_database_url,
        [("revision", at(MON, "09:00"), FAKE_IDS[0], NOW), ("revision", at(TUE, "09:00"), FAKE_IDS[0], NOW)],
    )
    assert sorted(r[0] for r in results) == ["booked", "limit"], results
    assert count_for(db, FAKE_IDS[0]) == 1


def test_g10b_once_the_appointment_is_past_the_subject_can_book_again(db):
    assert book(db, "revision", at(MON, "09:00"), FAKE_IDS[0])[0] == "booked"
    later = at(MON, "12:00")  # the first appointment (9:00–9:30) is now in the past
    assert book(db, "revision", at(TUE, "16:00"), FAKE_IDS[0], now=later)[0] == "booked"


def test_g11_a_slot_with_no_free_professional_is_taken(db):
    assert book(db, "limpieza", at(MON, "09:00"), FAKE_IDS[0])[0] == "booked"
    taken = book(db, "limpieza", at(MON, "09:15"), FAKE_IDS[1])
    assert taken[0] == "taken"
    assert count_for(db, FAKE_IDS[1]) == 0


# === G12–G13: no double booking (NFR-07, R-05) ===


def test_g12_the_database_rejects_overlaps_for_the_same_professional(db):
    insert_raw(db, FAKE_IDS[0], "revision", at(MON, "09:00"), at(MON, "09:30"), "odontologa_1", "gabinete_1")
    with pytest.raises(psycopg.errors.ExclusionViolation):
        insert_raw(db, FAKE_IDS[1], "revision", at(MON, "09:15"), at(MON, "09:45"), "odontologa_1", "gabinete_2")


def test_g12_the_database_rejects_overlaps_for_the_same_room(db):
    insert_raw(db, FAKE_IDS[0], "revision", at(MON, "09:00"), at(MON, "09:30"), "odontologa_1", "gabinete_1")
    with pytest.raises(psycopg.errors.ExclusionViolation):
        insert_raw(db, FAKE_IDS[1], "revision", at(MON, "09:00"), at(MON, "09:30"), "odontologo_2", "gabinete_1")


def test_g12_back_to_back_and_cancelled_appointments_do_not_conflict(db):
    insert_raw(db, FAKE_IDS[0], "revision", at(MON, "09:00"), at(MON, "09:30"), "odontologa_1", "gabinete_1")
    insert_raw(db, FAKE_IDS[1], "revision", at(MON, "09:30"), at(MON, "10:00"), "odontologa_1", "gabinete_1")
    insert_raw(db, FAKE_IDS[2], "revision", at(MON, "09:00"), at(MON, "09:30"), "odontologa_1", "gabinete_1", status="cancelled")


def test_g13_nfr07_ten_concurrent_bookings_of_one_hygienist_slot(db, test_database_url):
    start = at(MON, "09:00")
    calls = [("limpieza", start, FAKE_IDS[i], NOW) for i in range(10)]

    def booked_rows():
        return db.execute(
            "SELECT count(*) FROM agenda_appointments WHERE starts_at = %s AND status = 'booked'"
            " AND subject IN (SELECT agenda_subject(x) FROM unnest(%s::text[]) x)",
            (start, FAKE_IDS),
        ).fetchone()[0]

    results = run_concurrently(test_database_url, calls)
    # NFR-07 first, and never retried: two booked rows in one slot fail at once, whatever else happened.
    n = booked_rows()
    assert n <= 1, f"NFR-07: {n} citas booked en el mismo hueco; resultados: {results}"
    # A connection that failed is the environment, not the agenda: clean up and repeat the round once.
    if connection_failed(results):
        first = results
        _cleanup(db)
        results = run_concurrently(test_database_url, calls)
        n = booked_rows()
        assert n <= 1, f"NFR-07: {n} citas booked en el mismo hueco; resultados: {results}"
        if connection_failed(results):
            pytest.fail(f"Fallo de conexión en las dos rondas: {first} / {results}")
    assert sorted(r[0] for r in results) == ["booked"] + ["taken"] * 9, results
    assert n == 1, results


def test_g13_two_dentists_take_two_concurrent_revisions_and_the_third_is_taken(db, test_database_url):
    start = at(MON, "09:00")
    results = run_concurrently(test_database_url, [("revision", start, FAKE_IDS[i], NOW) for i in range(3)])
    booked = [r for r in results if r[0] == "booked"]
    assert sorted(r[0] for r in results) == ["booked", "booked", "taken"], results
    assert {r[1] for r in booked} == DENTISTS
    assert len({r[2] for r in booked}) == 2


# === G15–G17: patient data, pseudonymization, retention ===


def test_g15_appointments_hold_only_the_planned_columns(db):
    cols = [r[0] for r in db.execute(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = 'public' AND table_name = 'agenda_appointments' ORDER BY ordinal_position"
    )]
    # SPEC-008 (005_move_cancel.sql) adds two operational columns, and SPEC-009 (006_reminders.sql) one
    # more, «Iré»; none holds patient data (MC21, RM19).
    assert cols == ["id", "subject", "type_code", "starts_at", "ends_at", "professional", "room", "status",
                    "channel", "created_at", "during", "cancelled_at", "replaced_by", "attendance_confirmed_at"]


def test_g15_no_stored_row_contains_the_telegram_id(db):
    book(db, "revision", at(MON, "09:00"), FAKE_IDS[0])
    book(db, "limpieza", at(MON, "09:00"), FAKE_IDS[1])
    (hits,) = db.execute(
        "SELECT count(*) FROM agenda_appointments a WHERE a::text LIKE ANY (%s)", ([f"%{i}%" for i in FAKE_IDS],)
    ).fetchone()
    assert hits == 0


def test_g16_subject_is_a_keyed_hmac_distinct_from_the_consent_subject(db):
    s = db.execute("SELECT agenda_subject(%s)", (FAKE_IDS[0],)).fetchone()[0]
    assert HEX64.match(s) and FAKE_IDS[0] not in s
    assert s != db.execute("SELECT consent_subject(%s)", (FAKE_IDS[0],)).fetchone()[0]
    unkeyed = db.execute("SELECT encode(sha256(convert_to('agenda:' || %s, 'UTF8')), 'hex')", (FAKE_IDS[0],)).fetchone()[0]
    assert s != unkeyed
    assert s == db.execute("SELECT agenda_subject(%s)", (FAKE_IDS[0],)).fetchone()[0]


@pytest.mark.parametrize("bad", [None, "", "abc", "-5"])
def test_g16_subject_rejects_anything_but_a_telegram_user_id(db, bad):
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("SELECT agenda_subject(%s)", (bad,))


def test_g16_no_new_key_table(db):
    rows = db.execute(
        "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind = 'r' AND relname LIKE %s",
        ("%key%",),
    ).fetchall()
    # G16 is about the agenda subject: it reuses the SPEC-006 key, with no key of its own. SPEC-009
    # adds reminder_key on purpose, to encrypt the reminder chat id (clarifications Q3, human 2026-11-23).
    assert sorted(rows) == [("consent_key",), ("reminder_key",)]


def test_g17_appointments_ended_more_than_30_days_ago_are_purged(db):
    real_now = datetime.now(MADRID)
    old_day, recent_day = (real_now - timedelta(days=31)).date(), (real_now - timedelta(days=29)).date()
    insert_raw(db, FAKE_IDS[0], "revision", at(old_day, "03:00"), at(old_day, "03:30"), "odontologa_1", "gabinete_1")
    insert_raw(db, FAKE_IDS[1], "revision", at(recent_day, "23:00"), at(recent_day, "23:30"), "odontologa_1", "gabinete_1")
    free_slots(db, "revision", at(MON, "00:00"), limit=1)  # any agenda call purges
    assert count_for(db, FAKE_IDS[0]) == 0
    assert count_for(db, FAKE_IDS[1]) == 1


def test_g17_the_purge_ignores_p_now(db):
    real_now = datetime.now(MADRID)
    recent = (real_now - timedelta(days=1)).date()
    insert_raw(db, FAKE_IDS[0], "revision", at(recent, "03:00"), at(recent, "03:30"), "odontologa_1", "gabinete_1")
    free_slots(db, "revision", at(MON, "00:00"), limit=1, now=real_now + timedelta(days=400))
    assert count_for(db, FAKE_IDS[0]) == 1


# === Daylight saving time (acceptance criterion, human 2026-11-22) ===


@pytest.mark.parametrize("change,sunday", _dst_weeks())
def test_dst_slots_and_appointments_keep_madrid_local_time(db, change, sunday):
    friday, monday = sunday - timedelta(days=2), sunday + timedelta(days=1)
    now = at(sunday - timedelta(days=3), "10:00")  # the Thursday before
    for day in (friday, monday):
        first = free_slots(db, "revision", at(day, "00:00"), limit=1, now=now)
        assert [local(s) for _, s, _, _ in first] == [local(at(day, "09:00"))]
    for i, day in enumerate((friday, monday)):
        result, _, _, s, e, _, _ = book(db, "limpieza", at(day, "09:00"), FAKE_IDS[10 + i], now=now)
        assert result == "booked"
        assert (s.astimezone(MADRID).strftime("%H:%M"), e.astimezone(MADRID).strftime("%H:%M")) == ("09:00", "09:45")
        assert e - s == timedelta(minutes=45)
    before, after = at(friday, "09:00").utcoffset(), at(monday, "09:00").utcoffset()
    expected = (timedelta(hours=1), timedelta(hours=2)) if change == "march" else (timedelta(hours=2), timedelta(hours=1))
    assert (before, after) == expected
    stored = db.execute(
        "SELECT to_char(starts_at AT TIME ZONE 'Europe/Madrid', 'HH24:MI') FROM agenda_appointments"
        " WHERE subject IN (agenda_subject(%s), agenda_subject(%s)) ORDER BY starts_at",
        (FAKE_IDS[10], FAKE_IDS[11]),
    ).fetchall()
    assert stored == [("09:00",), ("09:00",)]


# === Session time zone (found in E0: Neon sessions run in GMT) ===


@pytest.mark.parametrize("tz", ["GMT", "America/New_York", "Asia/Tokyo"])
def test_results_do_not_depend_on_the_session_time_zone(test_database_url, tz):
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        _cleanup(conn)
        try:
            conn.execute(f"SET TIME ZONE '{tz}'")
            slots = free_slots(conn, "limpieza", at(MON, "00:00"))
            assert [local(s) for _, s, _, _ in slots] == [
                local(at(MON, "09:00")), local(at(MON, "16:00")), local(at(TUE, "09:00"))
            ]
            assert book(conn, "limpieza", at(MON, "13:30"), FAKE_IDS[0])[:2] == ("invalid", "outside_hours")
            booked = book(conn, "limpieza", at(MON, "09:00"), FAKE_IDS[0])
            assert booked[0] == "booked" and local(booked[3]) == local(at(MON, "09:00"))
        finally:
            _cleanup(conn)


# === Public functions: no time parameter (human, 2026-11-22) ===


def test_public_functions_have_no_time_parameter(db):
    args = dict(db.execute(
        "SELECT proname, pg_get_function_arguments(oid) FROM pg_proc"
        " WHERE pronamespace = 'public'::regnamespace AND proname IN ('agenda_free_slots', 'agenda_book')"
    ).fetchall())
    assert set(args) == {"agenda_free_slots", "agenda_book"}
    for name, signature in args.items():
        assert "p_now" not in signature and "timestamp with time zone DEFAULT now()" not in signature, (name, signature)
    assert "p_from_id" in args["agenda_book"]


def test_public_functions_behave_like_their_at_versions_with_the_real_time(db):
    real_from = datetime.now(MADRID) + timedelta(days=3)
    public = db.execute(
        "SELECT result, starts_at, ends_at, professional FROM agenda_free_slots('revision', %s)", (real_from,)
    ).fetchall()
    internal = db.execute(
        "SELECT result, starts_at, ends_at, professional FROM agenda_free_slots_at('revision', %s, 3, now())",
        (real_from,),
    ).fetchall()
    assert public == internal and len(public) == 3
    booked = db.execute(
        "SELECT result, starts_at FROM agenda_book('revision', %s, %s)", (public[0][1], FAKE_IDS[0])
    ).fetchone()
    assert booked == ("booked", public[0][1])
    assert db.execute("SELECT result FROM agenda_book('revision', %s, %s)", (public[0][1], FAKE_IDS[0])).fetchone() == ("limit",)


# === G18: idempotent schema that leaves the other features alone (named "reapplying": excluded in the red run) ===


def _fingerprint(conn):
    kb = conn.execute("SELECT md5(coalesce(string_agg(f::text, '|' ORDER BY fragment_id), '')) FROM kb_fragments f").fetchone()[0]
    consent = conn.execute("SELECT count(*) FROM consent").fetchone()[0]
    subject = conn.execute("SELECT consent_subject(%s)", (FAKE_IDS[0],)).fetchone()[0]
    agenda = conn.execute(
        "SELECT (SELECT count(*) FROM agenda_professionals), (SELECT count(*) FROM agenda_rooms),"
        " (SELECT count(*) FROM agenda_types), (SELECT count(*) FROM agenda_hours), (SELECT count(*) FROM agenda_settings)"
    ).fetchone()
    return kb, consent, subject, agenda


def test_g18_reapplying_the_schema_changes_nothing_else(db):
    before = _fingerprint(db)
    agenda_before = db.execute("SELECT agenda_subject(%s)", (FAKE_IDS[0],)).fetchone()[0]
    apply_schema(db)
    apply_schema(db)
    assert _fingerprint(db) == before
    assert db.execute("SELECT agenda_subject(%s)", (FAKE_IDS[0],)).fetchone()[0] == agenda_before


def test_g18_reapplying_keeps_values_the_clinic_changed(db):
    db.execute("UPDATE agenda_settings SET horizon = interval '45 days'")
    try:
        apply_schema(db)
        assert db.execute("SELECT horizon FROM agenda_settings").fetchone()[0] == timedelta(days=45)
    finally:
        db.execute("UPDATE agenda_settings SET horizon = interval '30 days'")


def test_g18_the_schema_file_is_003_agenda():
    assert (ROOT / "app" / "infra" / "sql" / "003_agenda.sql").exists()
