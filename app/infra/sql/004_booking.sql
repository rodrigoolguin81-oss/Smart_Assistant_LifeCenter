-- SPEC-007 (specs/008-booking) BK19: the patient's next appointment, for /micita and the limit message.
-- Idempotent: safe to re-run. Creates two functions only; no table, and no change to the data of
-- kb_fragments, consent, consent_key or the agenda. Depends on 003_agenda.sql (agenda_subject,
-- agenda_purge, agenda_appointments).

-- With an explicit "now" (tests only; n8n calls agenda_my_next). Returns only the type code and the
-- times of the subject's earliest booked appointment that starts after now: no professional, room,
-- subject or id.
CREATE OR REPLACE FUNCTION agenda_my_next_at(p_from_id text, p_now timestamptz)
RETURNS TABLE (type_code text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    v_subject text;
BEGIN
    PERFORM agenda_purge();
    v_subject := agenda_subject(p_from_id);   -- rejects anything but a Telegram user id
    RETURN QUERY
        SELECT a.type_code, a.starts_at, a.ends_at
        FROM agenda_appointments a
        WHERE a.subject = v_subject
          AND a.status = 'booked'
          AND a.starts_at > p_now
        ORDER BY a.starts_at
        LIMIT 1;
END
$$;

-- Public (what n8n will call): no time parameter, always now().
CREATE OR REPLACE FUNCTION agenda_my_next(p_from_id text)
RETURNS TABLE (type_code text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    SELECT * FROM agenda_my_next_at(p_from_id, now());
$$;
