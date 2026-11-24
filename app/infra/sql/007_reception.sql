-- SPEC-010 (specs/011-reception-handoff): reception handoff, complaints and ratings. Idempotent.
-- No message text and no subject is ever stored: a handoff row holds a code, a reason, the chat id
-- encrypted with the SPEC-009 helpers (reminder_key, decision D4), the group message id and its times.
-- The reception group id lives only in reception_settings (decision D2), filled by the human.

-- --- Settings: the reception group, one row (D2) ---------------------------------------------------
CREATE TABLE IF NOT EXISTS reception_settings (
    singleton         boolean     PRIMARY KEY DEFAULT true CHECK (singleton),
    reception_chat_id text        NOT NULL CHECK (reception_chat_id ~ '^-100[0-9]{5,15}$'),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON reception_settings FROM PUBLIC;

-- --- Handoffs (RH3–RH11, RH19) ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reception_handoffs (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    code             text        NOT NULL UNIQUE CHECK (code ~ '^[RQ]-[ABCDEFGHJKMNPQRSTUVWXYZ2-9]{4}$'),
    reason           text        NOT NULL CHECK (reason IN ('a', 'u', 'p', 'q')),
    chat_id_enc      bytea       NOT NULL,
    status           text        NOT NULL DEFAULT 'awaiting_text' CHECK (status IN ('awaiting_text', 'open')),
    group_message_id bigint      UNIQUE,
    created_at       timestamptz NOT NULL,
    opened_at        timestamptz,
    CHECK ((status = 'open') = (group_message_id IS NOT NULL AND opened_at IS NOT NULL)),
    CHECK ((reason = 'q') = (code LIKE 'Q-%'))
);
REVOKE ALL ON reception_handoffs FROM PUBLIC;

-- --- Ratings (RH16–RH18): counts only, no subject, no chat id, no text -----------------------------
CREATE TABLE IF NOT EXISTS feedback_daily (
    day    date    NOT NULL,
    reason text    NOT NULL CHECK (reason ~ '^[a-z_]{1,32}$'),
    up     integer NOT NULL DEFAULT 0 CHECK (up >= 0),
    down   integer NOT NULL DEFAULT 0 CHECK (down >= 0),
    PRIMARY KEY (day, reason)
);

-- --- Purge (RH6, RH10, RH20): 30 minutes waiting for the text, 48 hours open ------------------------
CREATE OR REPLACE FUNCTION handoff_purge_at(p_now timestamptz) RETURNS integer
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
DECLARE v_n integer;
BEGIN
    DELETE FROM reception_handoffs h
    WHERE (h.status = 'awaiting_text' AND h.created_at <= p_now - interval '30 minutes')
       OR (h.status = 'open' AND h.opened_at <= p_now - interval '48 hours');
    GET DIAGNOSTICS v_n = ROW_COUNT;
    RETURN v_n;
END
$$;

-- The patient's handoffs, found by the decrypted chat id (no subject is stored; the table is small).
CREATE OR REPLACE FUNCTION handoff_of_chat(p_chat_id text) RETURNS SETOF reception_handoffs
LANGUAGE sql STABLE SET search_path = public, pg_temp
AS $$ SELECT h.* FROM reception_handoffs h WHERE agenda_chat_decrypt(h.chat_id_enc) = p_chat_id; $$;

-- --- RH3: «Sí, pasar a recepción» → a new handoff waiting for the text, with a new code ------------
-- A patient has at most one handoff waiting for its text: a new one replaces the old.
CREATE OR REPLACE FUNCTION handoff_start_at(p_chat_id text, p_reason text, p_now timestamptz) RETURNS text
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
DECLARE
    v_alpha constant text := 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
    v_enc   bytea;
    v_code  text;
    v_bytes bytea;
BEGIN
    IF p_reason IS NULL OR p_reason NOT IN ('a', 'u', 'p', 'q') THEN
        RAISE EXCEPTION 'handoff_start: unknown reason %', p_reason;
    END IF;
    v_enc := agenda_chat_encrypt(p_chat_id);   -- rejects anything but a private chat id
    PERFORM handoff_purge_at(p_now);
    DELETE FROM reception_handoffs h WHERE h.status = 'awaiting_text' AND h.id IN (SELECT id FROM handoff_of_chat(p_chat_id));
    FOR i IN 1..20 LOOP
        v_bytes := gen_random_bytes(4);
        v_code := CASE WHEN p_reason = 'q' THEN 'Q-' ELSE 'R-' END
            || substr(v_alpha, get_byte(v_bytes, 0) % 31 + 1, 1) || substr(v_alpha, get_byte(v_bytes, 1) % 31 + 1, 1)
            || substr(v_alpha, get_byte(v_bytes, 2) % 31 + 1, 1) || substr(v_alpha, get_byte(v_bytes, 3) % 31 + 1, 1);
        BEGIN
            INSERT INTO reception_handoffs (code, reason, chat_id_enc, created_at) VALUES (v_code, p_reason, v_enc, p_now);
            RETURN v_code;
        EXCEPTION WHEN unique_violation THEN
            -- another open handoff has this code: draw again
        END;
    END LOOP;
    RAISE EXCEPTION 'handoff_start: no free code';
END
$$;

-- For the consent lookup in A: does a handoff of this chat wait for its text? (RH4)
CREATE OR REPLACE FUNCTION handoff_awaiting_at(p_chat_id text, p_now timestamptz) RETURNS boolean
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
BEGIN
    PERFORM handoff_purge_at(p_now);
    RETURN EXISTS (SELECT 1 FROM handoff_of_chat(p_chat_id) h WHERE h.status = 'awaiting_text');
END
$$;

-- RH4: the waiting handoff of this chat, to post the patient's text (nothing changes until it is posted).
CREATE OR REPLACE FUNCTION handoff_pending_at(p_chat_id text, p_now timestamptz)
RETURNS TABLE (id uuid, code text, reason text)
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
BEGIN
    PERFORM handoff_purge_at(p_now);
    RETURN QUERY SELECT h.id, h.code, h.reason FROM handoff_of_chat(p_chat_id) h WHERE h.status = 'awaiting_text';
END
$$;

-- RH4: posted in the group → open, with the group message id.
CREATE OR REPLACE FUNCTION handoff_open_at(p_id uuid, p_group_message_id bigint, p_now timestamptz) RETURNS text
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
BEGIN
    UPDATE reception_handoffs h SET status = 'open', group_message_id = p_group_message_id, opened_at = p_now
    WHERE h.id = p_id AND h.status = 'awaiting_text';
    RETURN CASE WHEN FOUND THEN 'open' ELSE 'not_found' END;
END
$$;

-- RH8: posting failed → the handoff goes.
CREATE OR REPLACE FUNCTION handoff_fail(p_id uuid) RETURNS text
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
BEGIN
    DELETE FROM reception_handoffs h WHERE h.id = p_id AND h.status = 'awaiting_text';
    RETURN CASE WHEN FOUND THEN 'deleted' ELSE 'not_found' END;
END
$$;

-- RH9, RH11: reception replied to a group message → the open handoff's code and the decrypted chat id,
-- or no row (closed, expired or unknown). The reply text never reaches the database.
CREATE OR REPLACE FUNCTION handoff_reply_at(p_group_message_id bigint, p_now timestamptz)
RETURNS TABLE (code text, chat_id text)
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
BEGIN
    PERFORM handoff_purge_at(p_now);
    RETURN QUERY SELECT h.code, agenda_chat_decrypt(h.chat_id_enc) FROM reception_handoffs h
                 WHERE h.group_message_id = p_group_message_id AND h.status = 'open';
END
$$;

-- RH10: «Cerrar» → the row (and its encrypted chat id) is deleted.
CREATE OR REPLACE FUNCTION handoff_close(p_code text) RETURNS text
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
BEGIN
    DELETE FROM reception_handoffs h WHERE h.code = p_code AND h.status = 'open';
    RETURN CASE WHEN FOUND THEN 'closed' ELSE 'not_found' END;
END
$$;

-- RH21: withdrawing consent deletes the patient's handoffs. In a private chat the chat id is the from.id.
CREATE OR REPLACE FUNCTION handoff_forget(p_chat_id text) RETURNS boolean
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
DECLARE v_n integer;
BEGIN
    DELETE FROM reception_handoffs h WHERE h.id IN (SELECT id FROM handoff_of_chat(p_chat_id));
    GET DIAGNOSTICS v_n = ROW_COUNT;
    RETURN v_n > 0;
END
$$;

-- RH17: 👍 / 👎 → +1 on the Madrid day and the reason of the rated reply. Nothing else.
CREATE OR REPLACE FUNCTION feedback_add_at(p_reason text, p_value text, p_now timestamptz) RETURNS text
LANGUAGE plpgsql VOLATILE SET search_path = public, pg_temp
AS $$
DECLARE v_day date := (p_now AT TIME ZONE 'Europe/Madrid')::date;
BEGIN
    IF p_value NOT IN ('up', 'down') THEN RAISE EXCEPTION 'feedback_add: unknown value %', p_value; END IF;
    INSERT INTO feedback_daily AS f (day, reason, up, down)
    VALUES (v_day, p_reason, CASE WHEN p_value = 'up' THEN 1 ELSE 0 END, CASE WHEN p_value = 'down' THEN 1 ELSE 0 END)
    ON CONFLICT (day, reason) DO UPDATE
        SET up = f.up + EXCLUDED.up, down = f.down + EXCLUDED.down;
    RETURN 'counted';
END
$$;

-- For A: the reception group id (D2), or NULL when the human has not stored it yet.
CREATE OR REPLACE FUNCTION reception_chat_id() RETURNS text
LANGUAGE sql STABLE SET search_path = public, pg_temp
AS $$ SELECT s.reception_chat_id FROM reception_settings s; $$;

-- --- Public functions (what n8n calls): no time parameter, always now() -----------------------------
CREATE OR REPLACE FUNCTION handoff_purge() RETURNS integer
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT handoff_purge_at(now()); $$;
CREATE OR REPLACE FUNCTION handoff_start(p_chat_id text, p_reason text) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT handoff_start_at(p_chat_id, p_reason, now()); $$;
CREATE OR REPLACE FUNCTION handoff_awaiting(p_chat_id text) RETURNS boolean
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT handoff_awaiting_at(p_chat_id, now()); $$;
CREATE OR REPLACE FUNCTION handoff_pending(p_chat_id text) RETURNS TABLE (id uuid, code text, reason text)
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT * FROM handoff_pending_at(p_chat_id, now()); $$;
CREATE OR REPLACE FUNCTION handoff_open(p_id uuid, p_group_message_id bigint) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT handoff_open_at(p_id, p_group_message_id, now()); $$;
CREATE OR REPLACE FUNCTION handoff_reply(p_group_message_id bigint) RETURNS TABLE (code text, chat_id text)
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT * FROM handoff_reply_at(p_group_message_id, now()); $$;
CREATE OR REPLACE FUNCTION feedback_add(p_reason text, p_value text) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp AS $$ SELECT feedback_add_at(p_reason, p_value, now()); $$;
