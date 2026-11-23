"""SPEC-008 M2 — agenda_cancel and agenda_move (specs/009-move-cancel; MC8, MC16–MC23, MC30).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main` (conftest refuses it).
Fake Telegram ids 900801… only; every appointment of those ids is removed before and after each
test. Dates are computed from today, as in test_agenda_sql.py. The consent key is never selected.

Interface under test (plan Step 2, spec MC21):
  agenda_cancel_at(from_id, start, now)         -> (result, type_code, starts_at, ends_at)
  agenda_cancel(from_id, start)                 -> same, uses now()
  agenda_move_at(from_id, old, new, now)        -> (result, reason, type_code, old_starts_at, old_ends_at,
                                                    starts_at, ends_at)
  agenda_move(from_id, old, new)                -> same, uses now()
  agenda_appointments.cancelled_at, .replaced_by; agenda_settings.change_min_lead (2 hours, example)
"""

import threading
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest

from app.infra.schema import apply_schema

MADRID = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parents[2]
FAKE_IDS = [str(900801 + i) for i in range(10)]
A, B = FAKE_IDS[0], FAKE_IDS[1]


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def at(day: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(day, time(h, m), MADRID)


MON = _next_monday(date.today() + timedelta(days=14))
if MON.month == 8:
    MON = _next_monday(date(MON.year, 9, 1))
TUE, WED = MON + timedelta(days=1), MON + timedelta(days=2)
SUN = MON - timedelta(days=1)
NOW = at(MON - timedelta(days=3), "07:00")  # the Friday before, 7:00 Madrid

CANCEL_COLS = ["result", "type_code", "starts_at", "ends_at"]
MOVE_COLS = ["result", "reason", "type_code", "old_starts_at", "old_ends_at", "starts_at", "ends_at"]


def _cleanup(conn) -> None:
    if conn.execute("SELECT to_regproc('public.agenda_subject') IS NOT NULL").fetchone()[0]:
        conn.execute(
            "DELETE FROM agenda_appointments WHERE subject IN (SELECT agenda_subject(x) FROM unnest(%s::text[]) x)",
            (FAKE_IDS,),
        )


@pytest.fixture
def db(test_db):
    _cleanup(test_db)
    yield test_db
    _cleanup(test_db)


def book(conn, type_code, start, from_id, now=NOW):
    return conn.execute(
        "SELECT result, reason, appointment_id FROM agenda_book_at(%s, %s, %s, %s)", (type_code, start, from_id, now)
    ).fetchone()


def booked(conn, type_code, start, from_id):
    """Books through the real primitive and returns the new appointment's id."""
    result, reason, appointment_id = book(conn, type_code, start, from_id)
    assert result == "booked", (result, reason)
    return appointment_id


def cancel(conn, from_id, start, now=NOW):
    return conn.execute("SELECT * FROM agenda_cancel_at(%s, %s, %s)", (from_id, start, now)).fetchone()


def move(conn, from_id, old, new, now=NOW):
    return conn.execute("SELECT * FROM agenda_move_at(%s, %s, %s, %s)", (from_id, old, new, now)).fetchone()


def rows_of(conn, from_id):
    """Every appointment of the subject, oldest first, as comparable tuples."""
    return conn.execute(
        "SELECT id, type_code, starts_at, ends_at, professional, room, status, cancelled_at, replaced_by"
        " FROM agenda_appointments WHERE subject = agenda_subject(%s) ORDER BY created_at, starts_at",
        (from_id,),
    ).fetchall()


def my_next(conn, from_id, now=NOW):
    return conn.execute("SELECT type_code, starts_at FROM agenda_my_next_at(%s, %s)", (from_id, now)).fetchall()


def run_concurrently(url, calls):
    """Run (sql, args) calls at the same moment, one connection per call, behind a barrier."""
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(i, sql, args):
        try:
            with psycopg.connect(url, autocommit=True) as conn:
                barrier.wait()
                results[i] = conn.execute(sql, args).fetchone()
        except Exception as exc:  # recorded, so the test reports it instead of hanging
            results[i] = ("exception", type(exc).__name__, str(exc))

    threads = [threading.Thread(target=worker, args=(i, sql, args)) for i, (sql, args) in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


# === Schema additions (MC8, MC19, MC21) ===


def test_settings_have_change_min_lead_of_two_hours_marked_as_example(db):
    assert db.execute("SELECT change_min_lead, ejemplo FROM agenda_settings").fetchall() == [(timedelta(hours=2), True)]


def test_new_appointments_have_no_cancelled_at_and_no_replaced_by(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    assert [(r[7], r[8]) for r in rows_of(db, A)] == [(None, None)]


# === Cancel (MC6–MC9, MC17, MC18) ===


def test_cancel_sets_the_row_cancelled_and_frees_the_slot(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    free_before = db.execute("SELECT starts_at FROM agenda_free_slots_at('limpieza', %s, 1, %s)", (at(MON, "09:00"), NOW)).fetchone()
    assert free_before[0] != at(MON, "09:00")  # the only hygienist is busy at 9:00

    assert cancel(db, A, at(MON, "09:00")) == ("cancelled", "limpieza", at(MON, "09:00"), at(MON, "09:45"))
    (row,) = rows_of(db, A)
    assert row[6] == "cancelled" and row[7] == NOW and row[8] is None

    free_after = db.execute("SELECT starts_at FROM agenda_free_slots_at('limpieza', %s, 1, %s)", (at(MON, "09:00"), NOW)).fetchone()
    assert free_after[0] == at(MON, "09:00")
    assert my_next(db, A) == []
    assert book(db, "revision", at(TUE, "09:00"), A)[0] == "booked"  # the limit counts only booked rows


def test_cancel_returns_exactly_its_columns(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    cur = db.execute("SELECT * FROM agenda_cancel_at(%s, %s, %s)", (A, at(MON, "09:00"), NOW))
    assert [d.name for d in cur.description] == CANCEL_COLS


@pytest.mark.parametrize("case", ["another_subject", "wrong_start", "already_cancelled", "past"])
def test_cancel_not_found_changes_nothing(db, case):
    booked(db, "limpieza", at(MON, "09:00"), A)
    if case == "already_cancelled":
        cancel(db, A, at(MON, "09:00"))
    before = rows_of(db, A)
    who, start, now = {
        "another_subject": (B, at(MON, "09:00"), NOW),
        "wrong_start": (A, at(MON, "09:15"), NOW),
        "already_cancelled": (A, at(MON, "09:00"), NOW),
        "past": (A, at(MON, "09:00"), at(MON, "12:00")),
    }[case]
    assert cancel(db, who, start, now) == ("not_found", None, None, None)
    assert rows_of(db, A) == before


def test_cancel_too_late_inside_the_minimum_notice_changes_nothing(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    before = rows_of(db, A)
    assert cancel(db, A, at(MON, "09:00"), now=at(MON, "07:30")) == ("too_late", "limpieza", at(MON, "09:00"), at(MON, "09:45"))
    assert rows_of(db, A) == before


def test_cancel_exactly_at_the_minimum_notice_is_allowed(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    assert cancel(db, A, at(MON, "09:00"), now=at(MON, "07:00"))[0] == "cancelled"


def test_a_double_cancel_at_the_same_time_gives_one_cancelled_and_one_not_found(db, test_database_url):
    booked(db, "limpieza", at(MON, "09:00"), A)
    sql = "SELECT result FROM agenda_cancel_at(%s, %s, %s)"
    results = run_concurrently(test_database_url, [(sql, (A, at(MON, "09:00"), NOW))] * 2)
    assert sorted(r[0] for r in results) == ["cancelled", "not_found"], results


# === Move (MC13–MC16, MC20) ===


def test_move_books_the_new_slot_and_cancels_the_old_one(db):
    old_id = booked(db, "limpieza", at(MON, "09:00"), A)
    assert move(db, A, at(MON, "09:00"), at(TUE, "09:00")) == (
        "moved", None, "limpieza", at(MON, "09:00"), at(MON, "09:45"), at(TUE, "09:00"), at(TUE, "09:45"))
    old, new = rows_of(db, A)
    assert old[0] == old_id and old[6] == "cancelled" and old[7] == NOW and old[8] == new[0]
    assert new[1:4] == ("limpieza", at(TUE, "09:00"), at(TUE, "09:45"))
    assert new[6] == "booked" and new[7] is None and new[8] is None
    assert my_next(db, A) == [("limpieza", at(TUE, "09:00"))]


def test_move_returns_exactly_its_columns(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    cur = db.execute("SELECT * FROM agenda_move_at(%s, %s, %s, %s)", (A, at(MON, "09:00"), at(TUE, "09:00"), NOW))
    assert [d.name for d in cur.description] == MOVE_COLS


def test_move_fifteen_minutes_later_with_the_same_professional_works(db):
    booked(db, "limpieza", at(MON, "09:00"), A)  # the hygienist is the only one who does limpieza
    assert move(db, A, at(MON, "09:00"), at(MON, "09:15"))[0] == "moved"
    old, new = rows_of(db, A)
    assert new[4] == old[4] == "higienista" and new[2] == at(MON, "09:15")


def test_move_into_a_taken_slot_keeps_the_old_appointment(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    booked(db, "limpieza", at(TUE, "09:00"), B)  # the hygienist is now busy on Tuesday at 9:00
    before = rows_of(db, A)
    assert move(db, A, at(MON, "09:00"), at(TUE, "09:00")) == (
        "taken", None, "limpieza", at(MON, "09:00"), at(MON, "09:45"), None, None)
    assert rows_of(db, A) == before


@pytest.mark.parametrize("new, now, reason", [
    (lambda: at(TUE, "09:10"), NOW, "not_on_grid"),
    (lambda: at(SUN, "10:00"), NOW, "closed"),
    (lambda: at(TUE, "13:30"), NOW, "outside_hours"),  # a 45-minute limpieza crosses 14:00
    (lambda: at(MON, "10:00"), at(MON, "08:30"), "too_soon"),  # old 12:00 is still > 2 h away
    (lambda: at(MON, "12:00"), NOW, "same_slot"),
])
def test_move_to_an_invalid_slot_keeps_the_old_appointment(db, new, now, reason):
    booked(db, "limpieza", at(MON, "12:00"), A)
    before = rows_of(db, A)
    result = move(db, A, at(MON, "12:00"), new(), now=now)
    assert result[:3] == ("invalid", reason, "limpieza") and result[5:] == (None, None)
    assert rows_of(db, A) == before


def test_move_too_late_inside_the_minimum_notice_keeps_the_old_appointment(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    before = rows_of(db, A)
    assert move(db, A, at(MON, "09:00"), at(TUE, "09:00"), now=at(MON, "07:30"))[0] == "too_late"
    assert rows_of(db, A) == before


@pytest.mark.parametrize("case", ["another_subject", "wrong_start", "already_moved"])
def test_move_not_found_changes_nothing(db, case):
    booked(db, "limpieza", at(MON, "09:00"), A)
    if case == "already_moved":
        move(db, A, at(MON, "09:00"), at(TUE, "09:00"))
    before = rows_of(db, A)
    who, old = {"another_subject": (B, at(MON, "09:00")), "wrong_start": (A, at(MON, "09:15")),
                "already_moved": (A, at(MON, "09:00"))}[case]
    result = move(db, who, old, at(WED, "09:00"))
    assert result == ("not_found", None, None, None, None, None, None)
    assert rows_of(db, A) == before
    assert rows_of(db, B) == []


def test_two_patients_moving_into_the_same_slot_give_one_moved_and_one_taken(db, test_database_url):
    booked(db, "limpieza", at(MON, "09:00"), A)
    booked(db, "limpieza", at(MON, "10:00"), B)
    sql = "SELECT result FROM agenda_move_at(%s, %s, %s, %s)"
    results = run_concurrently(test_database_url, [
        (sql, (A, at(MON, "09:00"), at(TUE, "09:00"), NOW)),
        (sql, (B, at(MON, "10:00"), at(TUE, "09:00"), NOW)),
    ])
    assert sorted(r[0] for r in results) == ["moved", "taken"], results
    loser = A if results[1][0] == "moved" else B
    loser_start = at(MON, "09:00") if loser == A else at(MON, "10:00")
    assert my_next(db, loser) == [("limpieza", loser_start)]  # the loser keeps their appointment
    (n,) = db.execute(
        "SELECT count(*) FROM agenda_appointments WHERE status = 'booked' AND starts_at = %s"
        " AND subject IN (SELECT agenda_subject(x) FROM unnest(%s::text[]) x)", (at(TUE, "09:00"), FAKE_IDS)
    ).fetchone()
    assert n == 1


def test_a_move_and_a_booking_of_the_same_subject_give_one_moved_and_one_limit(db, test_database_url):
    booked(db, "limpieza", at(MON, "09:00"), A)
    results = run_concurrently(test_database_url, [
        ("SELECT result FROM agenda_move_at(%s, %s, %s, %s)", (A, at(MON, "09:00"), at(TUE, "09:00"), NOW)),
        ("SELECT result FROM agenda_book_at(%s, %s, %s, %s)", ("revision", at(WED, "09:00"), A, NOW)),
    ])
    assert [r[0] for r in results] == ["moved", "limit"], results
    assert my_next(db, A) == [("limpieza", at(TUE, "09:00"))]


# === Privacy, public functions, input (MC22) ===


def test_public_functions_have_no_time_parameter(db):
    args = dict(db.execute(
        "SELECT proname, pg_get_function_arguments(oid) FROM pg_proc"
        " WHERE pronamespace = 'public'::regnamespace AND proname IN ('agenda_cancel', 'agenda_move')"
    ).fetchall())
    assert args == {
        "agenda_cancel": "p_from_id text, p_start timestamp with time zone",
        "agenda_move": "p_from_id text, p_old_start timestamp with time zone, p_new_start timestamp with time zone",
    }


def test_public_functions_behave_like_their_at_versions_with_the_real_time(db):
    real_from = datetime.now(MADRID) + timedelta(days=3)
    slots = db.execute(
        "SELECT starts_at FROM agenda_free_slots('limpieza', %s, 2) WHERE result = 'free'", (real_from,)
    ).fetchall()
    first, second = slots[0][0], slots[1][0]
    assert db.execute("SELECT result FROM agenda_book('limpieza', %s, %s)", (first, A)).fetchone()[0] == "booked"
    assert db.execute("SELECT result FROM agenda_move(%s, %s, %s)", (A, first, second)).fetchone()[0] == "moved"
    assert db.execute("SELECT result FROM agenda_cancel(%s, %s)", (A, second)).fetchone()[0] == "cancelled"
    assert my_next(db, A, now=datetime.now(MADRID)) == []


@pytest.mark.parametrize("bad", [None, "", "abc"])
def test_reject_anything_but_a_telegram_user_id(db, bad):
    with pytest.raises(psycopg.errors.RaiseException):
        cancel(db, bad, at(MON, "09:00"))
    with pytest.raises(psycopg.errors.RaiseException):
        move(db, bad, at(MON, "09:00"), at(TUE, "09:00"))


@pytest.mark.parametrize("tz", ["GMT", "America/New_York", "Asia/Tokyo"])
def test_results_do_not_depend_on_the_session_time_zone(test_database_url, tz):
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        _cleanup(conn)
        try:
            conn.execute(f"SET TIME ZONE '{tz}'")
            booked(conn, "limpieza", at(MON, "09:00"), A)
            assert move(conn, A, at(MON, "09:00"), at(TUE, "09:00"))[5:] == (at(TUE, "09:00"), at(TUE, "09:45"))
            assert cancel(conn, A, at(TUE, "09:00"))[2:] == (at(TUE, "09:00"), at(TUE, "09:45"))
        finally:
            _cleanup(conn)


# --- Schema (named "reapplying"/"schema_file_is": excluded in the red run, as in SPEC-004 E2) ---


def _fingerprint(conn):
    one = lambda sql, *a: conn.execute(sql, a or None).fetchone()[0]
    return (
        one("SELECT md5(coalesce(string_agg(f::text, '|' ORDER BY fragment_id), '')) FROM kb_fragments f"),
        one("SELECT count(*) FROM consent"),
        one("SELECT consent_subject(%s)", FAKE_IDS[0]),
        one("SELECT agenda_subject(%s)", FAKE_IDS[0]),
        one("SELECT md5(string_agg(t::text, '|' ORDER BY code)) FROM agenda_types t"),
        one("SELECT md5(string_agg(h::text, '|' ORDER BY weekday, start_time)) FROM agenda_hours h"),
        one("SELECT md5(s::text) FROM agenda_settings s"),
        one("SELECT md5(coalesce(string_agg(a::text, '|' ORDER BY id), '')) FROM agenda_appointments a"),
    )


def test_reapplying_the_schema_changes_nothing_else(db):
    booked(db, "limpieza", at(MON, "09:00"), A)
    move(db, A, at(MON, "09:00"), at(TUE, "09:00"))  # one cancelled row with replaced_by, one booked
    before = _fingerprint(db)
    apply_schema(db)
    apply_schema(db)
    assert _fingerprint(db) == before


def test_schema_file_is_005_move_cancel():
    assert (ROOT / "app" / "infra" / "sql" / "005_move_cancel.sql").exists()
