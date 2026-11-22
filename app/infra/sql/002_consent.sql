-- SPEC-006 (C17–C20): consent record keyed by an HMAC of the Telegram from.id.
-- Idempotent: safe to re-run. The key is generated inside the database, is kept on re-runs and
-- is never returned by any function. Accepted limitation: the key and the table are in the same
-- database (spec, Known limitations).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- One row, the 32-byte key. Created here with gen_random_bytes; ON CONFLICT keeps the existing key.
CREATE TABLE IF NOT EXISTS consent_key (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    key       bytea   NOT NULL CHECK (octet_length(key) = 32)
);
INSERT INTO consent_key (key) VALUES (gen_random_bytes(32)) ON CONFLICT (singleton) DO NOTHING;
REVOKE ALL ON consent_key FROM PUBLIC;

-- Only these four fields (C17): no id, chat id, name, username or message text; no rejections.
CREATE TABLE IF NOT EXISTS consent (
    subject      text        PRIMARY KEY CHECK (subject ~ '^[0-9a-f]{64}$'),
    status       text        NOT NULL CHECK (status IN ('accepted', 'revoked')),
    text_version text        NOT NULL CHECK (text_version <> ''),
    decided_at   timestamptz NOT NULL
);
REVOKE ALL ON consent FROM PUBLIC;

-- subject = HMAC-SHA256(from.id, key), hex (C18). Rejects anything but a Telegram user id.
CREATE OR REPLACE FUNCTION consent_subject(p_from_id text) RETURNS text
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_key bytea;
BEGIN
    IF p_from_id IS NULL OR p_from_id !~ '^[0-9]{1,20}$' THEN
        RAISE EXCEPTION 'consent_subject: invalid Telegram user id';
    END IF;
    SELECT k.key INTO v_key FROM consent_key k;
    IF v_key IS NULL THEN
        RAISE EXCEPTION 'consent_subject: consent key missing';
    END IF;
    RETURN encode(hmac(convert_to(p_from_id, 'UTF8'), v_key, 'sha256'), 'hex');
END
$$;

-- Withdrawn records are kept 30 days as proof, then deleted (C20). Called by every function below,
-- so no scheduled workflow is needed.
CREATE OR REPLACE FUNCTION consent_purge() RETURNS void
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    DELETE FROM consent WHERE status = 'revoked' AND decided_at < now() - interval '30 days';
$$;

-- The three functions n8n calls, with from.id as the query parameter $1.
CREATE OR REPLACE FUNCTION consent_get(p_from_id text)
RETURNS TABLE (status text, text_version text, decided_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
BEGIN
    PERFORM consent_purge();
    RETURN QUERY
        SELECT c.status, c.text_version, c.decided_at
        FROM consent c
        WHERE c.subject = consent_subject(p_from_id);
END
$$;

CREATE OR REPLACE FUNCTION consent_accept(p_from_id text, p_version text)
RETURNS TABLE (status text, text_version text, decided_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
BEGIN
    IF p_version IS NULL OR p_version = '' THEN
        RAISE EXCEPTION 'consent_accept: missing text version';
    END IF;
    PERFORM consent_purge();
    RETURN QUERY
        INSERT INTO consent AS c (subject, status, text_version, decided_at)
        VALUES (consent_subject(p_from_id), 'accepted', p_version, now())
        ON CONFLICT (subject) DO UPDATE
            SET status = 'accepted', text_version = EXCLUDED.text_version, decided_at = EXCLUDED.decided_at
        RETURNING c.status, c.text_version, c.decided_at;
END
$$;

CREATE OR REPLACE FUNCTION consent_revoke(p_from_id text)
RETURNS TABLE (status text, text_version text, decided_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
BEGIN
    PERFORM consent_purge();
    RETURN QUERY
        UPDATE consent AS c
        SET status = 'revoked', decided_at = now()
        WHERE c.subject = consent_subject(p_from_id) AND c.status = 'accepted'
        RETURNING c.status, c.text_version, c.decided_at;
END
$$;
