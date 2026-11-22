"""SPEC-007 R2 — agenda_my_next for /micita and the limit message (specs/008-booking; BK19, BK24).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main` (conftest refuses it).
Fake Telegram ids 900401… only; every appointment of those ids is removed before and after each
test. Dates are computed from today, as in test_agenda_sql.py. The consent key is never selected.

Interface under test (plan Step 2, spec BK19):
  agenda_my_next(from_id)          -> (type_code, starts_at, ends_at)   public, uses now()
  agenda_my_next_at(from_id, now)  -> same                              tests only
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest

from app.infra.schema import apply_schema

MADRID = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parents[2]
FAKE_IDS = [str(900401 + i) for i in range(10)]


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def at(day: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(day, time(h, m), MADRID)


MON = _next_monday(date.today() + timedelta(days=14))
if MON.month == 8:
    MON = _next_monday(date(MON.year, 9, 1))
TUE, WED = MON + timedelta(days=1), MON + timedelta(days=2)
NOW = at(MON - timedelta(days=3), "07:00")


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


def insert(conn, from_id, type_code, start, minutes, professional, room, status="booked"):
    conn.execute(
        "INSERT INTO agenda_appointments (subject, type_code, starts_at, ends_at, professional, room, status, channel)"
        " VALUES (agenda_subject(%s), %s, %s, %s, %s, %s, %s, 'telegram')",
        (from_id, type_code, start, start + timedelta(minutes=minutes), professional, room, status),
    )


def my_next(conn, from_id, now=NOW):
    return conn.execute("SELECT * FROM agenda_my_next_at(%s, %s)", (from_id, now)).fetchall()


def test_no_appointment_returns_nothing(db):
    assert my_next(db, FAKE_IDS[0]) == []


def test_returns_the_future_appointment_with_type_code_and_times(db):
    insert(db, FAKE_IDS[0], "limpieza", at(MON, "09:00"), 45, "higienista", "gabinete_1")
    rows = my_next(db, FAKE_IDS[0])
    assert rows == [("limpieza", at(MON, "09:00"), at(MON, "09:45"))]


def test_returns_the_earliest_of_several(db):
    insert(db, FAKE_IDS[0], "revision", at(WED, "16:00"), 30, "odontologa_1", "gabinete_1")
    insert(db, FAKE_IDS[0], "limpieza", at(TUE, "09:00"), 45, "higienista", "gabinete_2")
    insert(db, FAKE_IDS[0], "primera_visita", at(WED, "09:00"), 30, "odontologo_2", "gabinete_3")
    assert my_next(db, FAKE_IDS[0])[0][:2] == ("limpieza", at(TUE, "09:00"))


def test_past_and_cancelled_appointments_are_ignored(db):
    insert(db, FAKE_IDS[0], "revision", at(MON, "09:00"), 30, "odontologa_1", "gabinete_1")
    insert(db, FAKE_IDS[0], "limpieza", at(TUE, "09:00"), 45, "higienista", "gabinete_1", status="cancelled")
    assert my_next(db, FAKE_IDS[0], now=at(MON, "12:00")) == []  # 9:00 is past; Tuesday's is cancelled
    assert my_next(db, FAKE_IDS[0], now=at(MON, "08:59"))[0][0] == "revision"


def test_starting_exactly_now_is_not_next(db):
    insert(db, FAKE_IDS[0], "revision", at(MON, "09:00"), 30, "odontologa_1", "gabinete_1")
    assert my_next(db, FAKE_IDS[0], now=at(MON, "09:00")) == []


def test_another_subjects_appointment_is_invisible(db):
    insert(db, FAKE_IDS[1], "limpieza", at(MON, "09:00"), 45, "higienista", "gabinete_1")
    assert my_next(db, FAKE_IDS[0]) == []
    assert my_next(db, FAKE_IDS[1])[0][0] == "limpieza"


def test_returns_exactly_three_columns(db):
    insert(db, FAKE_IDS[0], "limpieza", at(MON, "09:00"), 45, "higienista", "gabinete_1")
    cur = db.execute("SELECT * FROM agenda_my_next_at(%s, %s)", (FAKE_IDS[0], NOW))
    assert [d.name for d in cur.description] == ["type_code", "starts_at", "ends_at"]
    public = db.execute("SELECT * FROM agenda_my_next(%s)", (FAKE_IDS[0],))
    assert [d.name for d in public.description] == ["type_code", "starts_at", "ends_at"]


def test_public_function_has_no_time_parameter_and_matches_the_at_version(db):
    signature = db.execute(
        "SELECT pg_get_function_arguments(oid) FROM pg_proc"
        " WHERE pronamespace = 'public'::regnamespace AND proname = 'agenda_my_next'"
    ).fetchall()
    assert signature == [("p_from_id text",)]
    soon = datetime.now(MADRID) + timedelta(days=5)
    insert(db, FAKE_IDS[0], "revision", soon.replace(second=0, microsecond=0), 30, "odontologa_1", "gabinete_1")
    public = db.execute("SELECT * FROM agenda_my_next(%s)", (FAKE_IDS[0],)).fetchall()
    internal = db.execute("SELECT * FROM agenda_my_next_at(%s, now())", (FAKE_IDS[0],)).fetchall()
    assert public == internal and len(public) == 1


@pytest.mark.parametrize("bad", [None, "", "abc"])
def test_rejects_anything_but_a_telegram_user_id(db, bad):
    with pytest.raises(psycopg.errors.RaiseException):
        my_next(db, bad)


def test_it_purges_appointments_ended_more_than_30_days_ago(db):
    old = (datetime.now(MADRID) - timedelta(days=31)).date()
    insert(db, FAKE_IDS[0], "revision", at(old, "03:00"), 30, "odontologa_1", "gabinete_1")
    my_next(db, FAKE_IDS[1])  # any agenda call purges (SPEC-004 G17)
    (n,) = db.execute(
        "SELECT count(*) FROM agenda_appointments WHERE subject = agenda_subject(%s)", (FAKE_IDS[0],)
    ).fetchone()
    assert n == 0


@pytest.mark.parametrize("tz", ["GMT", "America/New_York", "Asia/Tokyo"])
def test_does_not_depend_on_the_session_time_zone(test_database_url, tz):
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        _cleanup(conn)
        try:
            insert(conn, FAKE_IDS[0], "limpieza", at(MON, "09:00"), 45, "higienista", "gabinete_1")
            conn.execute(f"SET TIME ZONE '{tz}'")
            rows = my_next(conn, FAKE_IDS[0])
            assert rows[0][1] == at(MON, "09:00") and rows[0][2] == at(MON, "09:45")
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
    )


def test_reapplying_the_schema_changes_nothing_else(db):
    before = _fingerprint(db)
    apply_schema(db)
    apply_schema(db)
    assert _fingerprint(db) == before


def test_schema_file_is_004_booking():
    assert (ROOT / "app" / "infra" / "sql" / "004_booking.sql").exists()
