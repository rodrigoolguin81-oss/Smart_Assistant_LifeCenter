"""SPEC-010 H2 — reception handoff and ratings in Neon (specs/011-reception-handoff; RH3–RH11, RH16–RH22).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main` (conftest refuses it).
Fake private chat ids 901001… and the fake group id -1009010000001 only. Their handoffs, the settings
row and the test rating reasons are removed before and after each test. The keys are never selected.

Interface under test (plan Step 2):
  handoff_start_at(chat_id, reason, now)      / handoff_start(chat_id, reason)    -> code
  handoff_awaiting_at(chat_id, now)           / handoff_awaiting(chat_id)         -> boolean
  handoff_pending_at(chat_id, now)            / handoff_pending(chat_id)          -> (id, code, reason)
  handoff_open_at(id, group_message_id, now)  / handoff_open(id, group_message_id) -> open | not_found
  handoff_fail(id)                                                                 -> deleted | not_found
  handoff_reply_at(group_message_id, now)     / handoff_reply(group_message_id)   -> (code, chat_id)
  handoff_close(code)                                                              -> closed | not_found
  handoff_forget(chat_id)                                                          -> had_handoff
  handoff_purge_at(now)                       / handoff_purge()                   -> deleted rows
  feedback_add_at(reason, up|down, now)       / feedback_add(reason, up|down)     -> counted
  reception_chat_id()                                                              -> the group id or NULL
  reminder_claim_due_at (SPEC-009) also purges the handoffs (RH20)
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest

from app.infra.schema import apply_schema

MADRID = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parents[2]
CHATS = [str(901001 + i) for i in range(10)]
P1, P2, P3 = CHATS[0], CHATS[1], CHATS[2]
GROUP = "-1009010000001"
NOW = datetime(2026, 12, 2, 11, 0, tzinfo=MADRID)
VERSION = "1"
TEST_REASONS = ["test_spec_diez", "test_spec_diez_b"]
CODE = re.compile(r"^[RQ]-[ABCDEFGHJKMNPQRSTUVWXYZ2-9]{4}$")  # recepcion.js CODE_PATTERN


def one(conn, sql, *args):
    return conn.execute(sql, args or None).fetchone()[0]


def _has(conn, fn):
    return conn.execute("SELECT to_regproc(%s) IS NOT NULL", (f"public.{fn}",)).fetchone()[0]


def _cleanup(conn):
    if _has(conn, "handoff_forget"):
        for c in CHATS:
            conn.execute("SELECT handoff_forget(%s)", (c,))
    if conn.execute("SELECT to_regclass('public.reception_settings') IS NOT NULL").fetchone()[0]:
        conn.execute("DELETE FROM reception_settings WHERE reception_chat_id = %s", (GROUP,))
    if conn.execute("SELECT to_regclass('public.feedback_daily') IS NOT NULL").fetchone()[0]:
        conn.execute("DELETE FROM feedback_daily WHERE reason = ANY(%s)", (TEST_REASONS,))


@pytest.fixture
def db(test_db):
    _cleanup(test_db)
    yield test_db
    _cleanup(test_db)


def start(conn, chat, reason="a", now=NOW):
    return one(conn, "SELECT handoff_start_at(%s, %s, %s)", chat, reason, now)


def pending(conn, chat, now=NOW):
    return conn.execute("SELECT id, code, reason FROM handoff_pending_at(%s, %s)", (chat, now)).fetchall()


def open_(conn, hid, msg_id, now=NOW):
    return one(conn, "SELECT handoff_open_at(%s, %s, %s)", hid, msg_id, now)


def reply(conn, msg_id, now=NOW):
    return conn.execute("SELECT code, chat_id FROM handoff_reply_at(%s, %s)", (msg_id, now)).fetchall()


def rows_of(conn, chat):
    return conn.execute("SELECT code, reason, status, group_message_id, chat_id_enc IS NOT NULL FROM handoff_of_chat(%s)",
                        (chat,)).fetchall()


def opened(conn, chat, msg_id, reason="a", now=NOW):
    start(conn, chat, reason, now)
    (hid, code, _), = pending(conn, chat, now)
    assert open_(conn, hid, msg_id, now) == "open"
    return code


# === Schema (RH19, RH22): no text, no subject ===

def test_handoffs_hold_no_text_and_no_subject(db):
    cols = [r[0] for r in db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public'"
        " AND table_name = 'reception_handoffs' ORDER BY ordinal_position")]
    assert cols == ["id", "code", "reason", "chat_id_enc", "status", "group_message_id", "created_at", "opened_at"]


def test_feedback_daily_holds_only_counts(db):
    cols = [r[0] for r in db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public'"
        " AND table_name = 'feedback_daily' ORDER BY ordinal_position")]
    assert cols == ["day", "reason", "up", "down"]


def test_reception_settings_has_one_row_with_a_group_id(db):
    db.execute("INSERT INTO reception_settings (reception_chat_id) VALUES (%s)"
               " ON CONFLICT (singleton) DO UPDATE SET reception_chat_id = EXCLUDED.reception_chat_id", (GROUP,))
    assert one(db, "SELECT reception_chat_id()") == GROUP
    assert one(db, "SELECT count(*) FROM reception_settings") == 1
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO reception_settings (singleton, reception_chat_id) VALUES (false, %s)", (GROUP,))


@pytest.mark.parametrize("bad", ["900001", "-400", "-100abc", "", "-1001234"])
def test_reception_settings_rejects_anything_but_a_supergroup_id(db, bad):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO reception_settings (reception_chat_id) VALUES (%s)"
                   " ON CONFLICT (singleton) DO UPDATE SET reception_chat_id = EXCLUDED.reception_chat_id", (bad,))


# === Opening (RH3): code, encrypted chat id, one waiting handoff per patient ===

def test_start_stores_the_chat_id_encrypted_and_a_short_code(db):
    code = start(db, P1, "a")
    assert CODE.match(code) and code.startswith("R-")
    (row,) = rows_of(db, P1)
    assert row == (code, "a", "awaiting_text", None, True)
    raw = one(db, "SELECT chat_id_enc FROM reception_handoffs WHERE code = %s", code)
    assert P1.encode() not in bytes(raw)
    assert one(db, "SELECT handoff_awaiting_at(%s, %s)", P1, NOW) is True
    assert one(db, "SELECT handoff_awaiting_at(%s, %s)", P2, NOW) is False


def test_a_complaint_gets_the_q_prefix(db):
    assert start(db, P1, "q").startswith("Q-")


def test_a_second_start_replaces_the_waiting_one(db):
    start(db, P1, "a")
    code2 = start(db, P1, "u")
    assert [r[0] for r in rows_of(db, P1)] == [code2]


@pytest.mark.parametrize("bad_chat", ["-1001234567890", "abc", "", None])
def test_start_rejects_anything_but_a_private_chat_id(db, bad_chat):
    with pytest.raises(psycopg.errors.RaiseException):
        start(db, bad_chat)


def test_start_rejects_an_unknown_reason(db):
    with pytest.raises(psycopg.errors.RaiseException):
        start(db, P1, "x")


def test_codes_are_unique_among_existing_handoffs(db):
    codes = [start(db, c, "p") for c in CHATS]
    assert len(set(codes)) == len(codes) and all(CODE.match(c) for c in codes)
    assert one(db, "SELECT count(*) FROM reception_handoffs h WHERE h.code = ANY(%s)", codes) == len(codes)


# === Posting (RH4, RH8) ===

def test_posting_opens_the_handoff_with_the_group_message_id(db):
    code = start(db, P1, "a")
    (hid, c, reason), = pending(db, P1)
    assert (c, reason) == (code, "a")
    assert open_(db, hid, 4101) == "open"
    assert rows_of(db, P1) == [(code, "a", "open", 4101, True)]
    assert pending(db, P1) == [] and one(db, "SELECT handoff_awaiting_at(%s, %s)", P1, NOW) is False
    assert open_(db, hid, 4102) == "not_found"


def test_a_failed_post_deletes_the_handoff(db):
    start(db, P1)
    (hid, _, _), = pending(db, P1)
    assert one(db, "SELECT handoff_fail(%s)", hid) == "deleted"
    assert rows_of(db, P1) == []


# === Reception's reply (RH9, RH11): by the group message id ===

def test_a_reply_finds_the_patient_by_the_group_message_id(db):
    code = opened(db, P1, 4201)
    opened(db, P2, 4202)
    assert reply(db, 4201) == [(code, P1)]
    assert reply(db, 4201) == [(code, P1)]  # several replies while open
    assert reply(db, 9999) == []


def test_closing_deletes_the_row_and_a_later_reply_finds_nothing(db):
    code = opened(db, P1, 4301)
    assert one(db, "SELECT handoff_close(%s)", code) == "closed"
    assert rows_of(db, P1) == [] and reply(db, 4301) == []
    assert one(db, "SELECT handoff_close(%s)", code) == "not_found"


def test_a_waiting_handoff_cannot_be_closed_or_replied_to(db):
    code = start(db, P1)
    assert one(db, "SELECT handoff_close(%s)", code) == "not_found"
    assert rows_of(db, P1)[0][2] == "awaiting_text"


# === Expiry (RH6, RH10, RH20) ===

def test_a_waiting_handoff_expires_after_30_minutes(db):
    start(db, P1, now=NOW)
    assert one(db, "SELECT handoff_awaiting_at(%s, %s)", P1, NOW + timedelta(minutes=29)) is True
    assert one(db, "SELECT handoff_awaiting_at(%s, %s)", P1, NOW + timedelta(minutes=30)) is False
    assert rows_of(db, P1) == []


def test_an_open_handoff_closes_after_48_hours(db):
    code = opened(db, P1, 4401, now=NOW)
    assert reply(db, 4401, NOW + timedelta(hours=47, minutes=59)) == [(code, P1)]
    assert reply(db, 4401, NOW + timedelta(hours=48)) == []
    assert rows_of(db, P1) == []


def test_the_reminder_claim_also_purges_the_handoffs(db):
    opened(db, P1, 4501, now=NOW)
    start(db, P2, now=NOW)
    db.execute("SELECT * FROM reminder_claim_due_at(20, %s, %s)", (VERSION, NOW + timedelta(hours=48, minutes=1)))
    assert rows_of(db, P1) == [] and rows_of(db, P2) == []


# === Withdrawal (RH21) ===

def test_withdrawing_consent_deletes_the_patients_handoffs(db):
    opened(db, P1, 4601)
    start(db, P1, "q")
    opened(db, P2, 4602)
    assert one(db, "SELECT handoff_forget(%s)", P1) is True
    assert rows_of(db, P1) == [] and len(rows_of(db, P2)) == 1
    assert one(db, "SELECT handoff_forget(%s)", P1) is False


# === Ratings (RH17): a count per Madrid day and reason, nothing else ===

def test_ratings_are_counted_per_madrid_day_and_reason(db):
    r = TEST_REASONS[0]
    for v in ("up", "up", "down"):
        assert one(db, "SELECT feedback_add_at(%s, %s, %s)", r, v, NOW) == "counted"
    one(db, "SELECT feedback_add_at(%s, %s, %s)", r, "up", datetime(2026, 12, 2, 23, 30, tzinfo=MADRID))
    one(db, "SELECT feedback_add_at(%s, %s, %s)", r, "down", datetime(2026, 12, 3, 0, 10, tzinfo=MADRID))
    one(db, "SELECT feedback_add_at(%s, %s, %s)", TEST_REASONS[1], "up", NOW)
    rows = db.execute("SELECT day::text, reason, up, down FROM feedback_daily WHERE reason = ANY(%s) ORDER BY day, reason",
                      (TEST_REASONS,)).fetchall()
    assert rows == [("2026-12-02", r, 3, 1), ("2026-12-02", TEST_REASONS[1], 1, 0), ("2026-12-03", r, 0, 1)]


def test_an_unknown_rating_value_is_rejected(db):
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("SELECT feedback_add_at(%s, %s, %s)", (TEST_REASONS[0], "meh", NOW))


# === Public functions and no key out (RH19) ===

def test_public_functions_have_no_time_parameter(db):
    args = dict(db.execute(
        "SELECT p.proname, pg_get_function_identity_arguments(p.oid) FROM pg_proc p"
        " WHERE p.pronamespace = 'public'::regnamespace AND p.proname IN ('handoff_start', 'handoff_awaiting',"
        " 'handoff_pending', 'handoff_open', 'handoff_reply', 'handoff_purge', 'feedback_add')").fetchall())
    assert args == {
        "handoff_start": "p_chat_id text, p_reason text",
        "handoff_awaiting": "p_chat_id text",
        "handoff_pending": "p_chat_id text",
        "handoff_open": "p_id uuid, p_group_message_id bigint",
        "handoff_reply": "p_group_message_id bigint",
        "handoff_purge": "",
        "feedback_add": "p_reason text, p_value text",
    }


def test_public_start_and_reply_behave_like_their_at_versions(db):
    code = one(db, "SELECT handoff_start(%s, 'p')", P3)
    (hid, c, _), = db.execute("SELECT id, code, reason FROM handoff_pending(%s)", (P3,)).fetchall()
    assert c == code and one(db, "SELECT handoff_open(%s, 4701)", hid) == "open"
    assert db.execute("SELECT code, chat_id FROM handoff_reply(4701)").fetchall() == [(code, P3)]


def test_no_function_returns_bytes(db):
    n = one(db, "SELECT count(*) FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace"
                " AND (p.proname LIKE 'handoff%%' OR p.proname LIKE 'feedback%%' OR p.proname LIKE 'reception%%')"
                " AND (p.prorettype = 'bytea'::regtype OR 'bytea'::regtype = ANY(coalesce(p.proallargtypes, '{}')))")
    assert n == 0


# === Re-applying the schema (warned before running) ===

def _fingerprint(conn):
    return conn.execute(
        "SELECT (SELECT md5(coalesce(string_agg(h::text, '|' ORDER BY code), '')) FROM reception_handoffs h),"
        " (SELECT md5(coalesce(string_agg(f::text, '|' ORDER BY day, reason), '')) FROM feedback_daily f),"
        " (SELECT md5(coalesce(string_agg(s::text, '|'), '')) FROM reception_settings s),"
        " (SELECT md5(encode(key, 'hex')) FROM reminder_key)").fetchone()


def test_reapplying_the_schema_changes_nothing_else(db):
    opened(db, P1, 4801)
    one(db, "SELECT feedback_add_at(%s, 'up', %s)", TEST_REASONS[0], NOW)
    before = _fingerprint(db)
    apply_schema(db)
    apply_schema(db)
    assert _fingerprint(db) == before


def test_schema_file_is_007_reception():
    assert (ROOT / "app" / "infra" / "sql" / "007_reception.sql").exists()
