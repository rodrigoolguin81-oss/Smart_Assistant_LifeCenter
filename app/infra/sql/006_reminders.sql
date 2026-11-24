-- SPEC-009 (specs/010-reminders) RM7–RM17, RM19, RM24–RM26: reminders the day before an appointment.
-- Idempotent: safe to re-run. Adds two tables, one column, three settings, the functions and one
-- deferred trigger. It changes no existing row besides filling the new settings' defaults, and
-- touches neither kb_fragments, consent nor consent_key. Depends on 002–005. The SPEC-008 functions
-- agenda_cancel and agenda_move do not change (RM11).

-- --- The reminder key (RM8): generated here only if missing; never selected, printed or regenerated ---
CREATE TABLE IF NOT EXISTS reminder_key (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    key       bytea   NOT NULL CHECK (octet_length(key) = 32)
);
INSERT INTO reminder_key (key) VALUES (gen_random_bytes(32)) ON CONFLICT (singleton) DO NOTHING;
REVOKE ALL ON reminder_key FROM PUBLIC;

-- --- Schema additions (RM19, RM24) ---------------------------------------------------------------
-- «Iré» (decision Q6): an operational timestamp of the agenda, like cancelled_at. No patient data.
ALTER TABLE agenda_appointments ADD COLUMN IF NOT EXISTS attendance_confirmed_at timestamptz;
-- Example values until the clinic decides (DEP-03): 24 hours before, never 21:00–9:00 Madrid.
ALTER TABLE agenda_settings ADD COLUMN IF NOT EXISTS reminder_lead interval NOT NULL
    DEFAULT interval '24 hours' CHECK (reminder_lead > interval '0');
ALTER TABLE agenda_settings ADD COLUMN IF NOT EXISTS reminder_quiet_from time NOT NULL DEFAULT time '21:00';
ALTER TABLE agenda_settings ADD COLUMN IF NOT EXISTS reminder_quiet_to time NOT NULL DEFAULT time '09:00';

-- RM7, RM9: one row per appointment at most. The chat id is encrypted, and exists only while the
-- reminder is pending or being sent: a final row can never hold it (CHECK).
CREATE TABLE IF NOT EXISTS agenda_reminders (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id uuid        NOT NULL UNIQUE REFERENCES agenda_appointments (id) ON DELETE CASCADE,
    chat_id_enc    bytea,
    due_at         timestamptz NOT NULL,
    status         text        NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending', 'sending', 'sent', 'skipped', 'failed', 'blocked')),
    attempts       integer     NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    claimed_at     timestamptz,
    sent_at        timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT agenda_reminders_chat_id_only_while_open
        CHECK (status IN ('pending', 'sending') OR chat_id_enc IS NULL)
);
REVOKE ALL ON agenda_reminders FROM PUBLIC;

-- --- Internal helpers -----------------------------------------------------------------------------

-- RM7: encrypt and decrypt inside Postgres, with the reminder key (pgcrypto, already installed by 002).
CREATE OR REPLACE FUNCTION agenda_chat_encrypt(p_chat_id text) RETURNS bytea
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_chat_id IS NULL OR p_chat_id !~ '^[0-9]{1,20}$' THEN
        RAISE EXCEPTION 'agenda_chat_encrypt: invalid Telegram chat id';
    END IF;
    RETURN pgp_sym_encrypt(p_chat_id, (SELECT encode(k.key, 'hex') FROM reminder_key k));
END
$$;

CREATE OR REPLACE FUNCTION agenda_chat_decrypt(p_enc bytea) RETURNS text
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT CASE WHEN p_enc IS NULL THEN NULL
                ELSE pgp_sym_decrypt(p_enc, (SELECT encode(k.key, 'hex') FROM reminder_key k)) END;
$$;

-- The subject's booked appointment at that start, still in the future (the reminder buttons' rule,
-- as in SPEC-008 MC17).
CREATE OR REPLACE FUNCTION agenda_current_at(p_from_id text, p_start timestamptz, p_now timestamptz)
RETURNS agenda_appointments
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT a.* FROM agenda_appointments a
    WHERE a.subject = agenda_subject(p_from_id) AND a.status = 'booked'
      AND a.starts_at = p_start AND a.starts_at > p_now;
$$;

-- --- Opt-in: set, clear, state, forget (RM2–RM5, RM12) ----------------------------------------------

-- RM2: the opt-in window is 3 hours (clarifications Q7; citas.js REMINDER_OPT_IN_MINUTES).
CREATE OR REPLACE FUNCTION reminder_set_at(p_from_id text, p_start timestamptz, p_chat_id text, p_now timestamptz)
RETURNS text
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    a      agenda_appointments;
    v_lead interval;
    v_enc  bytea;
BEGIN
    PERFORM agenda_purge();
    v_enc := agenda_chat_encrypt(p_chat_id);   -- rejects anything but a chat id
    PERFORM pg_advisory_xact_lock(hashtextextended('agenda:' || agenda_subject(p_from_id), 0));
    a := agenda_current_at(p_from_id, p_start, p_now);
    IF a.id IS NULL THEN RETURN 'not_found'; END IF;
    IF a.starts_at < p_now + interval '3 hours' THEN RETURN 'too_late'; END IF;
    SELECT s.reminder_lead INTO v_lead FROM agenda_settings s;
    INSERT INTO agenda_reminders AS r (appointment_id, chat_id_enc, due_at)
    VALUES (a.id, v_enc, greatest(a.starts_at - v_lead, p_now))
    ON CONFLICT (appointment_id) DO UPDATE
        SET chat_id_enc = EXCLUDED.chat_id_enc, due_at = EXCLUDED.due_at, status = 'pending',
            attempts = 0, claimed_at = NULL, sent_at = NULL;
    RETURN 'set';
END
$$;

CREATE OR REPLACE FUNCTION reminder_clear_at(p_from_id text, p_start timestamptz, p_now timestamptz)
RETURNS text
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    a agenda_appointments;
BEGIN
    PERFORM agenda_purge();
    a := agenda_current_at(p_from_id, p_start, p_now);
    IF a.id IS NULL THEN RETURN 'not_found'; END IF;
    DELETE FROM agenda_reminders r WHERE r.appointment_id = a.id;
    RETURN 'cleared';
END
$$;

-- RM5: whether the subject's next booked appointment has an open reminder.
CREATE OR REPLACE FUNCTION reminder_state_at(p_from_id text, p_now timestamptz)
RETURNS boolean
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1 FROM agenda_reminders r
        WHERE r.status IN ('pending', 'sending')
          AND r.appointment_id = (SELECT a.id FROM agenda_appointments a
                                  WHERE a.subject = agenda_subject(p_from_id) AND a.status = 'booked'
                                    AND a.starts_at > p_now ORDER BY a.starts_at LIMIT 1));
$$;

-- RM9, RM12: on consent withdrawal, every open reminder of the subject goes, chat id included.
CREATE OR REPLACE FUNCTION reminder_forget(p_from_id text)
RETURNS boolean
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_n integer;
BEGIN
    DELETE FROM agenda_reminders r
    USING agenda_appointments a
    WHERE a.id = r.appointment_id AND a.subject = agenda_subject(p_from_id) AND r.status IN ('pending', 'sending');
    GET DIAGNOSTICS v_n = ROW_COUNT;
    RETURN v_n > 0;
END
$$;

-- RM19: «Iré» sets attendance_confirmed_at once.
CREATE OR REPLACE FUNCTION reminder_confirm_at(p_from_id text, p_start timestamptz, p_now timestamptz)
RETURNS text
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    a agenda_appointments;
BEGIN
    PERFORM agenda_purge();
    a := agenda_current_at(p_from_id, p_start, p_now);
    IF a.id IS NULL THEN RETURN 'not_found'; END IF;
    IF a.attendance_confirmed_at IS NOT NULL THEN RETURN 'already'; END IF;
    UPDATE agenda_appointments x SET attendance_confirmed_at = p_now WHERE x.id = a.id;
    RETURN 'confirmed';
END
$$;

-- --- Claim and mark (RM13–RM17): at most once -----------------------------------------------------

-- p_consent_version: CONSENT_TEXT_VERSION of consentimiento.js. A reminder goes only to a patient with
-- consent in force (SPEC-006 C22). The agenda subject cannot be turned into the consent subject, so the
-- consent is looked up from the decrypted chat id, which in a private chat is the from.id (A1).
CREATE OR REPLACE FUNCTION reminder_claim_due_at(p_limit integer, p_consent_version text, p_now timestamptz)
RETURNS TABLE (id uuid, chat_id text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    s       agenda_settings;
    v_local time;
BEGIN
    PERFORM agenda_purge();
    -- One claim at a time: two runs of C never claim the same row (RM16).
    PERFORM pg_advisory_xact_lock(hashtextextended('agenda:reminder_claim', 0));
    SELECT * INTO s FROM agenda_settings;

    -- 1. A row left in 'sending' for more than 1 hour is never sent again.
    UPDATE agenda_reminders r SET status = 'failed', chat_id_enc = NULL
    WHERE r.status = 'sending' AND r.claimed_at < p_now - interval '1 hour';

    -- 2. RM15: rows whose send window has closed, or whose patient has no consent in force.
    UPDATE agenda_reminders r SET status = 'skipped', chat_id_enc = NULL
    FROM agenda_appointments a
    WHERE a.id = r.appointment_id AND r.status = 'pending'
      AND (a.status <> 'booked'
           OR a.starts_at < p_now + s.change_min_lead
           OR NOT EXISTS (SELECT 1 FROM consent c
                          WHERE c.subject = consent_subject(agenda_chat_decrypt(r.chat_id_enc))
                            AND c.status = 'accepted' AND c.text_version = p_consent_version));

    -- 3. Quiet hours (Madrid): nothing is sent; the rows wait.
    v_local := (p_now AT TIME ZONE 'Europe/Madrid')::time;
    IF (s.reminder_quiet_from > s.reminder_quiet_to AND (v_local >= s.reminder_quiet_from OR v_local < s.reminder_quiet_to))
       OR (s.reminder_quiet_from < s.reminder_quiet_to AND v_local >= s.reminder_quiet_from AND v_local < s.reminder_quiet_to) THEN
        RETURN;
    END IF;

    -- 4. Claim the due rows, mark them 'sending', and return the decrypted chat id.
    RETURN QUERY
    WITH c AS (
        SELECT r.id FROM agenda_reminders r
        WHERE r.status = 'pending' AND r.due_at <= p_now
        ORDER BY r.due_at, r.id
        LIMIT p_limit
        FOR UPDATE SKIP LOCKED
    ), u AS (
        UPDATE agenda_reminders r SET status = 'sending', claimed_at = p_now, attempts = r.attempts + 1
        FROM c WHERE r.id = c.id
        RETURNING r.id, r.chat_id_enc, r.appointment_id
    )
    SELECT u.id, agenda_chat_decrypt(u.chat_id_enc), a.starts_at, a.ends_at
    FROM u JOIN agenda_appointments a ON a.id = u.appointment_id
    ORDER BY a.starts_at;
END
$$;

-- RM17: sent / blocked / retry. Only a row being sent changes; anything else is 'ignored'.
CREATE OR REPLACE FUNCTION reminder_mark_at(p_id uuid, p_result text, p_now timestamptz)
RETURNS text
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    r agenda_reminders;
    a agenda_appointments;
    v_min interval;
BEGIN
    IF p_result NOT IN ('sent', 'blocked', 'retry', 'failed') THEN
        RAISE EXCEPTION 'reminder_mark: unknown result %', p_result;
    END IF;
    SELECT * INTO r FROM agenda_reminders x WHERE x.id = p_id AND x.status = 'sending' FOR UPDATE;
    IF NOT FOUND THEN RETURN 'ignored'; END IF;
    IF p_result = 'sent' THEN
        UPDATE agenda_reminders x SET status = 'sent', sent_at = p_now, chat_id_enc = NULL WHERE x.id = p_id;
        RETURN 'sent';
    END IF;
    -- Human, 2026-11-24 (Q8): a 5xx or a network error may have been delivered: never retried.
    IF p_result = 'failed' THEN
        UPDATE agenda_reminders x SET status = 'failed', chat_id_enc = NULL WHERE x.id = p_id;
        RETURN 'failed';
    END IF;
    IF p_result = 'blocked' THEN
        UPDATE agenda_reminders x SET status = 'blocked', chat_id_enc = NULL WHERE x.id = p_id;
        RETURN 'blocked';
    END IF;
    SELECT * INTO a FROM agenda_appointments y WHERE y.id = r.appointment_id;
    SELECT s.change_min_lead INTO v_min FROM agenda_settings s;
    IF r.attempts < 3 AND a.status = 'booked' AND a.starts_at >= p_now + v_min THEN
        UPDATE agenda_reminders x SET status = 'pending', claimed_at = NULL WHERE x.id = p_id;
        RETURN 'pending';
    END IF;
    UPDATE agenda_reminders x SET status = 'failed', chat_id_enc = NULL WHERE x.id = p_id;
    RETURN 'failed';
END
$$;

-- --- The deferred trigger (RM10, RM11; human, plan review 2026-11-23) -----------------------------
-- It runs at the end of the transaction. agenda_move first cancels the old row and only then sets
-- replaced_by, so deciding at the first update would delete a reminder that should move. At commit:
-- replaced_by set → the open reminder moves to the new appointment; still NULL → it is deleted.
-- A move rolled back by its subtransaction ('taken') leaves no event, so the reminder stays.
CREATE OR REPLACE FUNCTION agenda_reminder_follow() RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    cur    agenda_appointments;
    newer  agenda_appointments;
    v_lead interval;
BEGIN
    SELECT * INTO cur FROM agenda_appointments x WHERE x.id = NEW.id;
    IF NOT FOUND OR cur.status <> 'cancelled' THEN RETURN NULL; END IF;
    IF cur.replaced_by IS NULL THEN
        DELETE FROM agenda_reminders r WHERE r.appointment_id = cur.id;
        RETURN NULL;
    END IF;
    SELECT * INTO newer FROM agenda_appointments x WHERE x.id = cur.replaced_by;
    SELECT s.reminder_lead INTO v_lead FROM agenda_settings s;
    UPDATE agenda_reminders r
       SET appointment_id = newer.id, due_at = greatest(newer.starts_at - v_lead, now()),
           status = 'pending', attempts = 0, claimed_at = NULL
     WHERE r.appointment_id = cur.id AND r.status = 'pending'
       AND NOT EXISTS (SELECT 1 FROM agenda_reminders o WHERE o.appointment_id = newer.id);
    RETURN NULL;
END
$$;

DROP TRIGGER IF EXISTS agenda_reminder_follow ON agenda_appointments;
CREATE CONSTRAINT TRIGGER agenda_reminder_follow
    AFTER UPDATE OF status, replaced_by ON agenda_appointments
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION agenda_reminder_follow();

-- --- Public functions (what n8n calls): no time parameter, always now() --------------------------

CREATE OR REPLACE FUNCTION reminder_set(p_from_id text, p_start timestamptz, p_chat_id text) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp
AS $$ SELECT reminder_set_at(p_from_id, p_start, p_chat_id, now()); $$;

CREATE OR REPLACE FUNCTION reminder_clear(p_from_id text, p_start timestamptz) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp
AS $$ SELECT reminder_clear_at(p_from_id, p_start, now()); $$;

CREATE OR REPLACE FUNCTION reminder_state(p_from_id text) RETURNS boolean
LANGUAGE sql VOLATILE SET search_path = public, pg_temp
AS $$ SELECT reminder_state_at(p_from_id, now()); $$;

CREATE OR REPLACE FUNCTION reminder_confirm(p_from_id text, p_start timestamptz) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp
AS $$ SELECT reminder_confirm_at(p_from_id, p_start, now()); $$;

CREATE OR REPLACE FUNCTION reminder_claim_due(p_limit integer, p_consent_version text)
RETURNS TABLE (id uuid, chat_id text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE sql VOLATILE SET search_path = public, pg_temp
AS $$ SELECT * FROM reminder_claim_due_at(p_limit, p_consent_version, now()); $$;

CREATE OR REPLACE FUNCTION reminder_mark(p_id uuid, p_result text) RETURNS text
LANGUAGE sql VOLATILE SET search_path = public, pg_temp
AS $$ SELECT reminder_mark_at(p_id, p_result, now()); $$;
