-- SPEC-008 (specs/009-move-cancel) MC8, MC16–MC23: cancelling and moving one's own appointment.
-- Idempotent: safe to re-run. Adds two columns to agenda_appointments, one setting, and four
-- functions. It changes no existing row besides filling the new setting's default, and touches
-- neither kb_fragments, consent nor consent_key. Depends on 003_agenda.sql and 004_booking.sql.

-- --- Schema additions (MC8, MC19, MC21) ---------------------------------------------------------

-- When an appointment was cancelled, and, after a move, the appointment that replaced it. Agenda
-- data, not patient data (MC21). Existing rows keep both empty.
ALTER TABLE agenda_appointments ADD COLUMN IF NOT EXISTS cancelled_at timestamptz;
ALTER TABLE agenda_appointments ADD COLUMN IF NOT EXISTS replaced_by uuid
    REFERENCES agenda_appointments (id) ON DELETE SET NULL;

-- MC19: until when the bot can still cancel or move (example value; the clinic decides, DEP-03).
ALTER TABLE agenda_settings ADD COLUMN IF NOT EXISTS change_min_lead interval NOT NULL
    DEFAULT interval '2 hours' CHECK (change_min_lead >= interval '0');

-- --- Internal functions with an explicit "now" (tests only; n8n calls the public ones) -----------

-- MC7, MC8, MC17, MC18: cancel the subject's booked appointment that starts at p_start.
CREATE OR REPLACE FUNCTION agenda_cancel_at(p_from_id text, p_start timestamptz, p_now timestamptz)
RETURNS TABLE (result text, type_code text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    v_subject text;
    v_lead    interval;
    a         agenda_appointments;
BEGIN
    PERFORM agenda_purge();
    v_subject := agenda_subject(p_from_id);   -- rejects anything but a Telegram user id
    -- The same lock as agenda_book_at: every write of one subject runs one at a time.
    PERFORM pg_advisory_xact_lock(hashtextextended('agenda:' || v_subject, 0));

    SELECT * INTO a FROM agenda_appointments x
    WHERE x.subject = v_subject AND x.status = 'booked' AND x.starts_at = p_start AND x.starts_at > p_now
    FOR UPDATE;
    IF NOT FOUND THEN   -- past, cancelled, moved, or not this subject's (MC17)
        RETURN QUERY SELECT 'not_found'::text, NULL::text, NULL::timestamptz, NULL::timestamptz;
        RETURN;
    END IF;

    SELECT s.change_min_lead INTO v_lead FROM agenda_settings s;
    IF a.starts_at < p_now + v_lead THEN   -- MC18
        RETURN QUERY SELECT 'too_late'::text, a.type_code, a.starts_at, a.ends_at;
        RETURN;
    END IF;

    UPDATE agenda_appointments x SET status = 'cancelled', cancelled_at = p_now WHERE x.id = a.id;
    RETURN QUERY SELECT 'cancelled'::text, a.type_code, a.starts_at, a.ends_at;
END
$$;

-- MC15, MC16, MC17, MC18, MC20: move the subject's booked appointment at p_old_start to
-- p_new_start, same type. All or nothing: on any result but 'moved', the old one is unchanged.
CREATE OR REPLACE FUNCTION agenda_move_at(p_from_id text, p_old_start timestamptz, p_new_start timestamptz,
                                          p_now timestamptz)
RETURNS TABLE (result text, reason text, type_code text, old_starts_at timestamptz, old_ends_at timestamptz,
               starts_at timestamptz, ends_at timestamptz)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    v_subject text;
    v_lead    interval;
    v_problem text;
    v_role    text;
    v_end     timestamptz;
    v_new     uuid;
    a         agenda_appointments;
    pro       record;
    rm        record;
BEGIN
    PERFORM agenda_purge();
    v_subject := agenda_subject(p_from_id);
    PERFORM pg_advisory_xact_lock(hashtextextended('agenda:' || v_subject, 0));

    SELECT * INTO a FROM agenda_appointments x
    WHERE x.subject = v_subject AND x.status = 'booked' AND x.starts_at = p_old_start AND x.starts_at > p_now
    FOR UPDATE;
    IF NOT FOUND THEN
        RETURN QUERY SELECT 'not_found'::text, NULL::text, NULL::text, NULL::timestamptz, NULL::timestamptz,
                            NULL::timestamptz, NULL::timestamptz;
        RETURN;
    END IF;

    SELECT s.change_min_lead INTO v_lead FROM agenda_settings s;
    IF a.starts_at < p_now + v_lead THEN
        RETURN QUERY SELECT 'too_late'::text, NULL::text, a.type_code, a.starts_at, a.ends_at,
                            NULL::timestamptz, NULL::timestamptz;
        RETURN;
    END IF;

    -- MC20: the new slot follows the booking rules for the same type; the same start is not a move.
    v_problem := CASE WHEN p_new_start = a.starts_at THEN 'same_slot'
                      ELSE agenda_slot_problem(a.type_code, p_new_start, p_now) END;
    IF v_problem IS NOT NULL THEN
        RETURN QUERY SELECT 'invalid'::text, v_problem, a.type_code, a.starts_at, a.ends_at,
                            NULL::timestamptz, NULL::timestamptz;
        RETURN;
    END IF;

    SELECT t.role, p_new_start + t.duration INTO v_role, v_end FROM agenda_types t WHERE t.code = a.type_code;

    -- One subtransaction: cancel the old row first, so a new time that overlaps it (same professional
    -- or room) does not trip the exclusion constraints, then try every professional and room as
    -- agenda_book_at does. If none is free, the raise rolls the cancellation back (MC16).
    BEGIN
        UPDATE agenda_appointments x SET status = 'cancelled', cancelled_at = p_now WHERE x.id = a.id;
        <<pairs>>
        FOR pro IN SELECT p.code FROM agenda_professionals p WHERE p.role = v_role ORDER BY p.code LOOP
            FOR rm IN SELECT r.code FROM agenda_rooms r ORDER BY r.code LOOP
                BEGIN
                    INSERT INTO agenda_appointments AS x (subject, type_code, starts_at, ends_at, professional, room)
                    VALUES (v_subject, a.type_code, p_new_start, v_end, pro.code, rm.code)
                    RETURNING x.id INTO v_new;
                    EXIT pairs;
                EXCEPTION WHEN exclusion_violation THEN
                    NULL;  -- this professional or this room is busy then: try the next pair
                END;
            END LOOP;
        END LOOP;
        IF v_new IS NULL THEN
            RAISE EXCEPTION 'agenda_move: no free professional and room' USING ERRCODE = 'AGM01';
        END IF;
        UPDATE agenda_appointments x SET replaced_by = v_new WHERE x.id = a.id;
    EXCEPTION WHEN SQLSTATE 'AGM01' THEN
        RETURN QUERY SELECT 'taken'::text, NULL::text, a.type_code, a.starts_at, a.ends_at,
                            NULL::timestamptz, NULL::timestamptz;
        RETURN;
    END;

    RETURN QUERY SELECT 'moved'::text, NULL::text, a.type_code, a.starts_at, a.ends_at, p_new_start, v_end;
END
$$;

-- --- Public functions (what n8n calls): no time parameter, always now() --------------------------

CREATE OR REPLACE FUNCTION agenda_cancel(p_from_id text, p_start timestamptz)
RETURNS TABLE (result text, type_code text, starts_at timestamptz, ends_at timestamptz)
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    SELECT * FROM agenda_cancel_at(p_from_id, p_start, now());
$$;

CREATE OR REPLACE FUNCTION agenda_move(p_from_id text, p_old_start timestamptz, p_new_start timestamptz)
RETURNS TABLE (result text, reason text, type_code text, old_starts_at timestamptz, old_ends_at timestamptz,
               starts_at timestamptz, ends_at timestamptz)
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    SELECT * FROM agenda_move_at(p_from_id, p_old_start, p_new_start, now());
$$;
