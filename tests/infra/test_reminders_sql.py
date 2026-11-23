"""SPEC-009 N2 — reminders in Neon (specs/010-reminders; RM7–RM17, RM19, RM24–RM26, RM29).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main` (conftest refuses it).
Fake Telegram ids 900901… only; their appointments (and, by cascade, reminders) and consent rows are
removed before and after each test. Dates are computed from today. The keys are never selected.

Interface under test (plan Step 2, spec RM24):
  reminder_set_at(from_id, start, chat_id, now) / reminder_set(from_id, start, chat_id) -> result
  reminder_clear_at(from_id, start, now)        / reminder_clear(from_id, start)        -> result
  reminder_state_at(from_id, now)               / reminder_state(from_id)               -> has_reminder
  reminder_forget(from_id)                                                               -> had_reminder
  reminder_confirm_at(from_id, start, now)      / reminder_confirm(from_id, start)      -> result
  reminder_claim_due_at(limit, version, now)    / reminder_claim_due(limit, version)    -> (id, chat_id, starts_at, ends_at)
  reminder_mark_at(id, result, now)             / reminder_mark(id, result)             -> status
  the deferred constraint trigger on agenda_appointments (a move takes the reminder along; a cancel deletes it)
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
FAKE_IDS = [str(900901 + i) for i in range(10)]
A, B, C = FAKE_IDS[0], FAKE_IDS[1], FAKE_IDS[2]
VERSION = "1"  # CONSENT_TEXT_VERSION of consentimiento.js


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def at(day: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(day, time(h, m), MADRID)


MON = _next_monday(date.today() + timedelta(days=14))
if MON.month == 8:
    MON = _next_monday(date(MON.year, 9, 1))
SUN, TUE, WED = MON - timedelta(days=1), MON + timedelta(days=1), MON + timedelta(days=2)
NOW = at(MON - timedelta(days=3), "07:00")  # the Friday before, 7:00 Madrid


def _cleanup(conn) -> None:
    if conn.execute("SELECT to_regproc('public.agenda_subject') IS NOT NULL").fetchone()[0]:
        conn.execute(
            "DELETE FROM agenda_appointments WHERE subject IN (SELECT agenda_subject(x) FROM unnest(%s::text[]) x)",
            (FAKE_IDS,),
        )
        conn.execute("DELETE FROM consent WHERE subject IN (SELECT consent_subject(x) FROM unnest(%s::text[]) x)", (FAKE_IDS,))


@pytest.fixture
def db(test_db):
    _cleanup(test_db)
    for fid in FAKE_IDS:
        consent(test_db, fid, "accepted")
    yield test_db
    _cleanup(test_db)


def consent(conn, from_id, status, version=VERSION):
    conn.execute(
        "INSERT INTO consent (subject, status, text_version, decided_at) VALUES (consent_subject(%s), %s, %s, now())"
        " ON CONFLICT (subject) DO UPDATE SET status = EXCLUDED.status, text_version = EXCLUDED.text_version",
        (from_id, status, version),
    )


def book(conn, type_code, start, from_id, now=NOW):
    result, reason = conn.execute("SELECT result, reason FROM agenda_book_at(%s, %s, %s, %s)",
                                  (type_code, start, from_id, now)).fetchone()
    assert result == "booked", (result, reason)


def one(conn, sql, *args):
    return conn.execute(sql, args or None).fetchone()[0]


def rset(conn, from_id, start, now=NOW, chat=None):
    return one(conn, "SELECT reminder_set_at(%s, %s, %s, %s)", from_id, start, from_id if chat is None else chat, now)


def claim(conn, now, limit=20):
    return conn.execute("SELECT id, chat_id, starts_at, ends_at FROM reminder_claim_due_at(%s, %s, %s)",
                        (limit, VERSION, now)).fetchall()


def mark(conn, rid, result, now):
    return one(conn, "SELECT reminder_mark_at(%s, %s, %s)", rid, result, now)


def reminders(conn, from_id):
    """The subject's reminder rows: (status, due_at, attempts, chat id present, sent_at, appointment start)."""
    return conn.execute(
        "SELECT r.status, r.due_at, r.attempts, r.chat_id_enc IS NOT NULL, r.sent_at, a.starts_at"
        " FROM agenda_reminders r JOIN agenda_appointments a ON a.id = r.appointment_id"
        " WHERE a.subject = agenda_subject(%s) ORDER BY a.created_at, a.starts_at", (from_id,)).fetchall()


def run_concurrently(url, calls):
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(i, sql, args):
        try:
            with psycopg.connect(url, autocommit=True) as conn:
                barrier.wait()
                results[i] = conn.execute(sql, args).fetchall()
        except Exception as exc:
            results[i] = [("exception", type(exc).__name__, str(exc))]

    threads = [threading.Thread(target=worker, args=(i, s, a)) for i, (s, a) in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


# === Schema additions (RM8, RM19, RM24) ===


def test_settings_hold_the_example_lead_and_quiet_hours(db):
    row = db.execute("SELECT reminder_lead, reminder_quiet_from, reminder_quiet_to, ejemplo FROM agenda_settings").fetchone()
    assert row == (timedelta(hours=24), time(21, 0), time(9, 0), True)


def test_the_reminder_key_exists_once_and_is_32_bytes(db):
    assert one(db, "SELECT count(*) FROM reminder_key") == 1
    assert one(db, "SELECT octet_length(key) = 32 FROM reminder_key") is True


def test_new_appointments_have_no_attendance_confirmation(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    assert one(db, "SELECT attendance_confirmed_at FROM agenda_appointments WHERE subject = agenda_subject(%s)", A) is None


# === Opt-in: set, clear, state (RM2–RM5, RM7) ===


def test_set_stores_the_chat_id_encrypted_and_due_24_hours_before(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    assert rset(db, A, at(MON, "09:00")) == "set"
    assert reminders(db, A) == [("pending", at(SUN, "09:00"), 0, True, None, at(MON, "09:00"))]
    enc = one(db, "SELECT r.chat_id_enc FROM agenda_reminders r JOIN agenda_appointments a ON a.id = r.appointment_id"
                  " WHERE a.subject = agenda_subject(%s)", A)
    assert A.encode() not in bytes(enc)  # never in clear text


def test_set_twice_keeps_one_row(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    assert rset(db, A, at(MON, "09:00")) == "set"
    assert len(reminders(db, A)) == 1


def test_set_less_than_24_hours_ahead_is_due_at_once(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    now = at(SUN, "12:00")
    assert rset(db, A, at(MON, "09:00"), now=now) == "set"
    assert reminders(db, A)[0][1] == now


def test_set_under_3_hours_is_too_late_and_stores_nothing(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    assert rset(db, A, at(MON, "09:00"), now=at(MON, "06:30")) == "too_late"
    assert reminders(db, A) == []


@pytest.mark.parametrize("case", ["another_subject", "wrong_start", "cancelled"])
def test_set_not_found_stores_nothing(db, case):
    book(db, "limpieza", at(MON, "09:00"), A)
    if case == "cancelled":
        db.execute("SELECT * FROM agenda_cancel_at(%s, %s, %s)", (A, at(MON, "09:00"), NOW))
    who, start = {"another_subject": (B, at(MON, "09:00")), "wrong_start": (A, at(MON, "09:15")),
                  "cancelled": (A, at(MON, "09:00"))}[case]
    assert rset(db, who, start) == "not_found"
    assert reminders(db, A) == [] and reminders(db, B) == []


@pytest.mark.parametrize("bad_chat", ["", "abc", "12 34"])
def test_set_rejects_anything_but_a_chat_id(db, bad_chat):
    book(db, "limpieza", at(MON, "09:00"), A)
    with pytest.raises(psycopg.errors.RaiseException):
        rset(db, A, at(MON, "09:00"), chat=bad_chat)


def test_state_and_clear(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    assert one(db, "SELECT reminder_state_at(%s, %s)", A, NOW) is False
    rset(db, A, at(MON, "09:00"))
    assert one(db, "SELECT reminder_state_at(%s, %s)", A, NOW) is True
    assert one(db, "SELECT reminder_clear_at(%s, %s, %s)", A, at(MON, "09:00"), NOW) == "cleared"
    assert reminders(db, A) == [] and one(db, "SELECT reminder_state_at(%s, %s)", A, NOW) is False
    assert one(db, "SELECT reminder_clear_at(%s, %s, %s)", A, at(MON, "09:15"), NOW) == "not_found"


def test_forget_deletes_the_reminder_and_says_whether_there_was_one(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    assert one(db, "SELECT reminder_forget(%s)", A) is True
    assert reminders(db, A) == []
    assert one(db, "SELECT reminder_forget(%s)", A) is False


# === The deferred trigger, through the real SPEC-008 functions (RM10, RM11; human, plan review) ===


def test_a_move_takes_the_reminder_to_the_new_appointment(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    assert db.execute("SELECT result FROM agenda_move_at(%s, %s, %s, %s)", (A, at(MON, "09:00"), at(WED, "16:00"), NOW)).fetchone()[0] == "moved"
    assert reminders(db, A) == [("pending", at(TUE, "16:00"), 0, True, None, at(WED, "16:00"))]
    assert one(db, "SELECT count(*) FROM agenda_reminders r JOIN agenda_appointments a ON a.id = r.appointment_id"
                   " WHERE a.subject = agenda_subject(%s) AND a.status = 'cancelled'", A) == 0


def test_a_cancel_deletes_the_reminder(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    assert db.execute("SELECT result FROM agenda_cancel_at(%s, %s, %s)", (A, at(MON, "09:00"), NOW)).fetchone()[0] == "cancelled"
    assert reminders(db, A) == []


def test_a_move_into_a_taken_slot_leaves_the_reminder_on_the_old_appointment(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    book(db, "limpieza", at(WED, "16:00"), B)  # the hygienist is busy then
    rset(db, A, at(MON, "09:00"))
    before = reminders(db, A)
    assert db.execute("SELECT result FROM agenda_move_at(%s, %s, %s, %s)", (A, at(MON, "09:00"), at(WED, "16:00"), NOW)).fetchone()[0] == "taken"
    assert reminders(db, A) == before


# === Claim: due, quiet hours, window, consent, at most once (RM13–RM16) ===


def test_nothing_is_claimed_before_it_is_due(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    assert claim(db, at(SUN, "08:45")) == []


def test_a_due_reminder_is_claimed_once_with_its_chat_id(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    rows = claim(db, at(SUN, "09:00"))
    assert [(r[1], r[2], r[3]) for r in rows] == [(A, at(MON, "09:00"), at(MON, "09:45"))]
    assert reminders(db, A)[0][:4] == ("sending", at(SUN, "09:00"), 1, True)
    assert claim(db, at(SUN, "09:15")) == []


def test_quiet_hours_wait_until_morning(db):
    book(db, "limpieza", at(WED, "16:00"), A)
    rset(db, A, at(WED, "16:00"))  # due Tuesday 16:00
    assert claim(db, at(TUE, "22:00")) == []
    assert claim(db, at(WED, "08:59")) == []
    assert len(claim(db, at(WED, "09:00"))) == 1


@pytest.mark.parametrize("now, why", [
    (lambda: at(MON, "07:30"), "less than 2 hours left"),
    (lambda: at(MON, "10:00"), "the appointment has started"),
])
def test_a_reminder_whose_window_closed_is_skipped_without_chat_id(db, now, why):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    assert claim(db, now()) == [], why
    assert reminders(db, A)[0][0] == "skipped" and reminders(db, A)[0][3] is False


@pytest.mark.parametrize("state, version", [("revoked", VERSION), ("accepted", "0")])
def test_no_consent_in_force_means_skipped(db, state, version):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    consent(db, A, state, version)
    assert claim(db, at(SUN, "09:00")) == []
    assert reminders(db, A)[0][0] == "skipped" and reminders(db, A)[0][3] is False


def test_a_stale_sending_row_becomes_failed_and_is_never_sent(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    claim(db, at(SUN, "09:00"))
    assert claim(db, at(SUN, "10:01")) == []
    assert reminders(db, A)[0][0] == "failed" and reminders(db, A)[0][3] is False


def test_two_claims_at_the_same_time_never_return_the_same_reminder(db, test_database_url):
    for fid, hh in ((A, "09:00"), (B, "10:00"), (C, "11:00")):
        book(db, "limpieza", at(MON, hh), fid)
        rset(db, fid, at(MON, hh))
    sql = "SELECT id FROM reminder_claim_due_at(%s, %s, %s)"
    results = run_concurrently(test_database_url, [(sql, (20, VERSION, at(SUN, "12:00")))] * 2)
    ids = [r[0] for rows in results for r in rows]
    assert all(r[0] != "exception" for rows in results for r in rows), results
    assert len(ids) == 3 and len(set(ids)) == 3


# === Mark (RM17), and the chat id gone once final (RM9) ===


def test_mark_sent_wipes_the_chat_id(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    (rid, *_), = claim(db, at(SUN, "09:00"))
    assert mark(db, rid, "sent", at(SUN, "09:01")) == "sent"
    assert reminders(db, A)[0] == ("sent", at(SUN, "09:00"), 1, False, at(SUN, "09:01"), at(MON, "09:00"))


def test_mark_blocked_wipes_the_chat_id(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    (rid, *_), = claim(db, at(SUN, "09:00"))
    assert mark(db, rid, "blocked", at(SUN, "09:01")) == "blocked"
    assert reminders(db, A)[0][0] == "blocked" and reminders(db, A)[0][3] is False


def test_retry_goes_back_to_pending_and_fails_after_three_attempts(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    for attempt, minute in ((1, "09:00"), (2, "09:15"), (3, "09:30")):
        (rid, *_), = claim(db, at(SUN, minute))
        expected = "pending" if attempt < 3 else "failed"
        assert mark(db, rid, "retry", at(SUN, minute)) == expected
    assert reminders(db, A)[0][:4] == ("failed", at(SUN, "09:00"), 3, False)


def test_retry_after_the_window_closed_fails(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    (rid, *_), = claim(db, at(SUN, "09:00"))
    assert mark(db, rid, "retry", at(MON, "07:30")) == "failed"


def test_mark_ignores_a_row_that_is_not_being_sent(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    rid = one(db, "SELECT r.id FROM agenda_reminders r JOIN agenda_appointments a ON a.id = r.appointment_id"
                  " WHERE a.subject = agenda_subject(%s)", A)
    assert mark(db, rid, "sent", at(SUN, "09:00")) == "ignored"
    assert reminders(db, A)[0][0] == "pending"


def test_a_final_row_can_never_hold_a_chat_id(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("UPDATE agenda_reminders SET status = 'sent' WHERE appointment_id IN"
                   " (SELECT id FROM agenda_appointments WHERE subject = agenda_subject(%s))", (A,))


# === «Iré» (RM19, decision Q6) ===


def test_confirm_records_attendance_once(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    assert one(db, "SELECT reminder_confirm_at(%s, %s, %s)", A, at(MON, "09:00"), at(SUN, "09:05")) == "confirmed"
    assert one(db, "SELECT reminder_confirm_at(%s, %s, %s)", A, at(MON, "09:00"), at(SUN, "10:00")) == "already"
    assert one(db, "SELECT attendance_confirmed_at FROM agenda_appointments WHERE subject = agenda_subject(%s)", A) == at(SUN, "09:05")
    assert one(db, "SELECT reminder_confirm_at(%s, %s, %s)", B, at(MON, "09:00"), at(SUN, "09:05")) == "not_found"


# === Privacy and public functions (RM25) ===


def test_public_functions_have_no_time_parameter(db):
    args = dict(db.execute(
        "SELECT proname, pg_get_function_arguments(oid) FROM pg_proc WHERE pronamespace = 'public'::regnamespace"
        " AND proname IN ('reminder_set', 'reminder_clear', 'reminder_state', 'reminder_forget', 'reminder_confirm',"
        " 'reminder_claim_due', 'reminder_mark')").fetchall())
    assert args == {
        "reminder_set": "p_from_id text, p_start timestamp with time zone, p_chat_id text",
        "reminder_clear": "p_from_id text, p_start timestamp with time zone",
        "reminder_state": "p_from_id text",
        "reminder_forget": "p_from_id text",
        "reminder_confirm": "p_from_id text, p_start timestamp with time zone",
        "reminder_claim_due": "p_limit integer, p_consent_version text",
        "reminder_mark": "p_id uuid, p_result text",
    }


def test_no_reminder_function_returns_bytes(db):
    results = db.execute("SELECT proname, pg_get_function_result(oid) FROM pg_proc WHERE pronamespace = 'public'::regnamespace"
                         " AND proname LIKE 'reminder\\_%'").fetchall()
    assert results and all("bytea" not in r for _, r in results), results


def test_public_set_and_claim_behave_like_their_at_versions(db):
    real = datetime.now(MADRID)
    slot = db.execute("SELECT starts_at FROM agenda_free_slots('limpieza', %s, 1) WHERE result = 'free'", (real + timedelta(days=3),)).fetchone()[0]
    assert db.execute("SELECT result FROM agenda_book('limpieza', %s, %s)", (slot, A)).fetchone()[0] == "booked"
    assert one(db, "SELECT reminder_set(%s, %s, %s)", A, slot, A) == "set"
    assert one(db, "SELECT reminder_state(%s)", A) is True
    assert db.execute("SELECT * FROM reminder_claim_due(20, %s)", (VERSION,)).fetchall() == []  # due in 2 days


# --- Schema (named "reapplying"/"schema_file_is": excluded in the red run, as in SPEC-004 E2) ---


def _fingerprint(conn):
    return (
        one(conn, "SELECT md5(coalesce(string_agg(f::text, '|' ORDER BY fragment_id), '')) FROM kb_fragments f"),
        one(conn, "SELECT md5(coalesce(string_agg(c::text, '|' ORDER BY subject), '')) FROM consent c"),
        one(conn, "SELECT md5(encode(key, 'hex')) FROM consent_key"),
        one(conn, "SELECT md5(encode(key, 'hex')) FROM reminder_key"),
        one(conn, "SELECT md5(s::text) FROM agenda_settings s"),
        one(conn, "SELECT md5(coalesce(string_agg(a::text, '|' ORDER BY id), '')) FROM agenda_appointments a"),
        one(conn, "SELECT md5(coalesce(string_agg(r::text, '|' ORDER BY id), '')) FROM agenda_reminders r"),
    )


def test_reapplying_the_schema_changes_nothing_else(db):
    book(db, "limpieza", at(MON, "09:00"), A)
    rset(db, A, at(MON, "09:00"))
    before = _fingerprint(db)
    apply_schema(db)
    apply_schema(db)
    assert _fingerprint(db) == before


def test_schema_file_is_006_reminders():
    assert (ROOT / "app" / "infra" / "sql" / "006_reminders.sql").exists()
