"""SPEC-006 K2 — consent table, key and functions in Neon (C17–C20; plan Step 2).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main`. Uses fake Telegram ids
900001… only, and deletes every row it creates. The consent key is never selected or printed:
only its length is checked.
"""

import re
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from app.infra.schema import apply_schema, main

FAKE_IDS = [str(900001 + i) for i in range(10)]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _functions_exist(conn) -> bool:
    (n,) = conn.execute(
        "SELECT count(*) FROM pg_proc WHERE proname = 'consent_subject' AND pronamespace = 'public'::regnamespace"
    ).fetchone()
    return n > 0


@pytest.fixture
def db(test_db):
    """Test-branch connection; removes the fake ids' rows before and after each test."""

    def cleanup():
        if _functions_exist(test_db):
            for fake in FAKE_IDS:
                test_db.execute("DELETE FROM consent WHERE subject = consent_subject(%s)", (fake,))

    cleanup()
    yield test_db
    cleanup()


def subject(conn, from_id: str) -> str:
    return conn.execute("SELECT consent_subject(%s)", (from_id,)).fetchone()[0]


def get(conn, from_id: str):
    return conn.execute("SELECT status, text_version, decided_at FROM consent_get(%s)", (from_id,)).fetchall()


def insert_synthetic(conn, from_id: str, status: str, age: timedelta) -> None:
    conn.execute(
        "INSERT INTO consent (subject, status, text_version, decided_at) VALUES (consent_subject(%s), %s, '1', now() - %s)",
        (from_id, status, age),
    )


# --- Subject: keyed HMAC of the id (C18) ---


def test_subject_is_a_keyed_hmac_and_not_the_id(db):
    s = subject(db, FAKE_IDS[0])
    assert HEX64.match(s)
    assert FAKE_IDS[0] not in s
    (unkeyed,) = db.execute("SELECT encode(sha256(convert_to(%s, 'UTF8')), 'hex')", (FAKE_IDS[0],)).fetchone()
    assert s != unkeyed, "the subject must be keyed, not a plain hash of the id"


def test_subject_is_stable_per_id_and_distinct_between_ids(db):
    assert subject(db, FAKE_IDS[0]) == subject(db, FAKE_IDS[0])
    assert subject(db, FAKE_IDS[0]) != subject(db, FAKE_IDS[1])


@pytest.mark.parametrize("bad", [None, "", "abc", "12 34", "-5"])
def test_subject_rejects_anything_but_a_telegram_user_id(db, bad):
    with pytest.raises(psycopg.errors.RaiseException):
        subject(db, bad)


# --- Lookup, accept, withdraw (C8, C10) ---


def test_unknown_id_has_no_record(db):
    assert get(db, FAKE_IDS[0]) == []


def test_accept_creates_an_accepted_record_with_the_version(db):
    rows = db.execute("SELECT status, text_version FROM consent_accept(%s, '1')", (FAKE_IDS[0],)).fetchall()
    assert rows == [("accepted", "1")]
    [(status, version, decided_at)] = get(db, FAKE_IDS[0])
    assert (status, version) == ("accepted", "1")
    assert datetime.now(timezone.utc) - decided_at < timedelta(minutes=5)


def test_accepting_again_replaces_the_record(db):
    db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[0],))
    db.execute("SELECT consent_accept(%s, '2')", (FAKE_IDS[0],))
    (n,) = db.execute("SELECT count(*) FROM consent WHERE subject = consent_subject(%s)", (FAKE_IDS[0],)).fetchone()
    assert n == 1
    assert [r[:2] for r in get(db, FAKE_IDS[0])] == [("accepted", "2")]


def test_accepting_after_withdrawing_makes_it_accepted_again(db):
    db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[0],))
    db.execute("SELECT consent_revoke(%s)", (FAKE_IDS[0],))
    db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[0],))
    assert [r[:2] for r in get(db, FAKE_IDS[0])] == [("accepted", "1")]


@pytest.mark.parametrize("bad_version", [None, ""])
def test_accept_rejects_a_missing_version(db, bad_version):
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("SELECT consent_accept(%s, %s)", (FAKE_IDS[0], bad_version))


def test_withdraw_marks_the_record_revoked(db):
    db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[0],))
    rows = db.execute("SELECT status, text_version FROM consent_revoke(%s)", (FAKE_IDS[0],)).fetchall()
    assert rows == [("revoked", "1")]
    assert [r[:2] for r in get(db, FAKE_IDS[0])] == [("revoked", "1")]


def test_withdraw_without_an_accepted_record_creates_nothing(db):
    assert db.execute("SELECT * FROM consent_revoke(%s)", (FAKE_IDS[0],)).fetchall() == []
    assert get(db, FAKE_IDS[0]) == []


# --- Purge of withdrawn records after 30 days, run by the consent functions (C20) ---


@pytest.mark.parametrize("call", ["get", "accept", "revoke"])
def test_each_function_purges_revoked_records_older_than_30_days(db, call):
    insert_synthetic(db, FAKE_IDS[1], "revoked", timedelta(days=31))
    insert_synthetic(db, FAKE_IDS[2], "revoked", timedelta(days=29))
    insert_synthetic(db, FAKE_IDS[3], "accepted", timedelta(days=400))

    if call == "get":
        get(db, FAKE_IDS[0])
    elif call == "accept":
        db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[0],))
    else:
        db.execute("SELECT consent_revoke(%s)", (FAKE_IDS[0],))

    assert db.execute("SELECT 1 FROM consent WHERE subject = consent_subject(%s)", (FAKE_IDS[1],)).fetchall() == []
    assert [r[0] for r in db.execute("SELECT status FROM consent WHERE subject = consent_subject(%s)", (FAKE_IDS[2],))] == ["revoked"]
    assert [r[0] for r in db.execute("SELECT status FROM consent WHERE subject = consent_subject(%s)", (FAKE_IDS[3],))] == ["accepted"]


# --- What is stored (C17) ---


def test_consent_table_has_exactly_the_four_columns(db):
    cols = [r[0] for r in db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'consent' ORDER BY ordinal_position"
    )]
    assert cols == ["subject", "status", "text_version", "decided_at"]


def test_no_stored_row_contains_the_id(db):
    db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[0],))
    db.execute("SELECT consent_accept(%s, '1')", (FAKE_IDS[1],))
    db.execute("SELECT consent_revoke(%s)", (FAKE_IDS[1],))
    (hits,) = db.execute(
        "SELECT count(*) FROM consent c WHERE c::text LIKE ANY (%s)", ([f"%{i}%" for i in FAKE_IDS],)
    ).fetchone()
    assert hits == 0


def test_status_only_accepts_accepted_or_revoked(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO consent VALUES (consent_subject(%s), 'rejected', '1', now())", (FAKE_IDS[0],))


# --- The key (C19) ---


def test_there_is_one_32_byte_key(db):
    rows = db.execute("SELECT octet_length(key) FROM consent_key").fetchall()
    assert rows == [(32,)]


def test_reapplying_the_schema_keeps_the_key(db):
    before = subject(db, FAKE_IDS[0])
    apply_schema(db)
    apply_schema(db)
    assert subject(db, FAKE_IDS[0]) == before
    assert db.execute("SELECT count(*) FROM consent_key").fetchone() == (1,)


# --- Command line (plan Step 2: apply the schema without re-ingesting kb/) ---


def test_cli_applies_the_schema_and_prints_only_the_host(test_database_url, capsys):
    assert main(["--database-url-env", "TEST_DATABASE_URL"]) == 0
    out = capsys.readouterr().out
    host = psycopg.conninfo.conninfo_to_dict(test_database_url)["host"]
    assert host in out
    password = psycopg.conninfo.conninfo_to_dict(test_database_url).get("password")
    assert not password or password not in out


def test_cli_requires_the_variable_name(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_cli_fails_when_the_variable_is_not_set(monkeypatch, capsys):
    monkeypatch.delenv("CONSENT_TEST_MISSING_URL", raising=False)
    assert main(["--database-url-env", "CONSENT_TEST_MISSING_URL"]) == 2
