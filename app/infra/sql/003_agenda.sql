-- SPEC-004 (specs/007-agenda): the project's own appointment agenda (RES-01).
-- Idempotent: safe to re-run. It does not touch kb_fragments, consent or consent_key.
-- Every Madrid local-time conversion is explicit (AT TIME ZONE 'Europe/Madrid'): Neon sessions run
-- in GMT and n8n's may differ, so nothing here depends on the session TimeZone (task E0).

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- --- Configuration (G1–G3), every row marked ejemplo until DEP-01/DEP-03 -------------------------

CREATE TABLE IF NOT EXISTS agenda_settings (
    singleton              boolean  PRIMARY KEY DEFAULT true CHECK (singleton),
    slot_minutes           integer  NOT NULL CHECK (slot_minutes > 0 AND 60 % slot_minutes = 0),
    min_lead               interval NOT NULL CHECK (min_lead >= interval '0'),
    horizon                interval NOT NULL CHECK (horizon > interval '0'),
    max_future_per_subject integer  NOT NULL CHECK (max_future_per_subject >= 1),
    ejemplo                boolean  NOT NULL DEFAULT true
);
INSERT INTO agenda_settings (slot_minutes, min_lead, horizon, max_future_per_subject)
VALUES (15, interval '2 hours', interval '30 days', 1)
ON CONFLICT (singleton) DO NOTHING;

-- Opening blocks by ISO weekday (1 = Monday) and the months they apply in (Q15: no August afternoons).
CREATE TABLE IF NOT EXISTS agenda_hours (
    weekday    smallint   NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    start_time time       NOT NULL,
    end_time   time       NOT NULL,
    months     smallint[] NOT NULL CHECK (cardinality(months) > 0
                                          AND months <@ ARRAY[1,2,3,4,5,6,7,8,9,10,11,12]::smallint[]),
    ejemplo    boolean    NOT NULL DEFAULT true,
    PRIMARY KEY (weekday, start_time),
    CHECK (start_time < end_time)
);
INSERT INTO agenda_hours (weekday, start_time, end_time, months)
SELECT wd, b.s, b.e, b.m
FROM generate_series(1, 5) AS wd,
     (VALUES (time '09:00', time '14:00', ARRAY[1,2,3,4,5,6,7,8,9,10,11,12]::smallint[]),
             (time '16:00', time '20:00', ARRAY[1,2,3,4,5,6,7,9,10,11,12]::smallint[])) AS b(s, e, m)
UNION ALL
SELECT 6, time '10:00', time '14:00', ARRAY[1,2,3,4,5,6,7,8,9,10,11,12]::smallint[]
ON CONFLICT (weekday, start_time) DO NOTHING;

CREATE TABLE IF NOT EXISTS agenda_closures (
    day    date PRIMARY KEY,
    reason text NOT NULL
);

CREATE TABLE IF NOT EXISTS agenda_professionals (
    code    text    PRIMARY KEY,
    name    text    NOT NULL,
    role    text    NOT NULL CHECK (role IN ('dentist', 'hygienist')),
    ejemplo boolean NOT NULL DEFAULT true
);
INSERT INTO agenda_professionals (code, name, role) VALUES
    ('odontologa_1', 'Odontóloga 1', 'dentist'),
    ('odontologo_2', 'Odontólogo 2', 'dentist'),
    ('higienista',   'Higienista',   'hygienist')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS agenda_rooms (
    code    text    PRIMARY KEY,
    name    text    NOT NULL,
    ejemplo boolean NOT NULL DEFAULT true
);
INSERT INTO agenda_rooms (code, name) VALUES
    ('gabinete_1', 'Gabinete 1'), ('gabinete_2', 'Gabinete 2'), ('gabinete_3', 'Gabinete 3')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS agenda_types (
    code            text     PRIMARY KEY,
    name            text     NOT NULL,
    duration        interval CHECK (duration > interval '0'),
    role            text     NOT NULL CHECK (role IN ('dentist', 'hygienist')),
    bookable_by_bot boolean  NOT NULL,
    ejemplo         boolean  NOT NULL DEFAULT true,
    CHECK (NOT bookable_by_bot OR duration IS NOT NULL)
);
INSERT INTO agenda_types (code, name, duration, role, bookable_by_bot) VALUES
    ('revision',          'Revisión',                                       interval '30 minutes', 'dentist',   true),
    ('limpieza',          'Limpieza',                                       interval '45 minutes', 'hygienist', true),
    ('primera_visita',    'Primera visita',                                 interval '30 minutes', 'dentist',   true),
    ('blanqueamiento',    'Blanqueamiento',                                 interval '90 minutes', 'dentist',   false),
    ('tratamiento_largo', 'Implantes, ortodoncia u otro tratamiento largo', NULL,                  'dentist',   false)
ON CONFLICT (code) DO NOTHING;

-- --- Appointments (G12, G15): only the subject about the patient; no double booking ---------------

CREATE TABLE IF NOT EXISTS agenda_appointments (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    subject      text        NOT NULL CHECK (subject ~ '^[0-9a-f]{64}$'),
    type_code    text        NOT NULL REFERENCES agenda_types (code),
    starts_at    timestamptz NOT NULL,
    ends_at      timestamptz NOT NULL,
    professional text        NOT NULL REFERENCES agenda_professionals (code),
    room         text        NOT NULL REFERENCES agenda_rooms (code),
    status       text        NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled')),
    channel      text        NOT NULL DEFAULT 'telegram' CHECK (channel IN ('telegram')),
    created_at   timestamptz NOT NULL DEFAULT now(),
    during       tstzrange   GENERATED ALWAYS AS (tstzrange(starts_at, ends_at, '[)')) STORED,
    CHECK (starts_at < ends_at),
    CONSTRAINT agenda_no_double_professional
        EXCLUDE USING gist (professional WITH =, during WITH &&) WHERE (status = 'booked'),
    CONSTRAINT agenda_no_double_room
        EXCLUDE USING gist (room WITH =, during WITH &&) WHERE (status = 'booked')
);
CREATE INDEX IF NOT EXISTS agenda_appointments_subject_idx ON agenda_appointments (subject);

REVOKE ALL ON agenda_settings, agenda_hours, agenda_closures, agenda_professionals, agenda_rooms,
              agenda_types, agenda_appointments FROM PUBLIC;

-- G3: a professional only takes types of their own role, whoever inserts.
CREATE OR REPLACE FUNCTION agenda_check_role() RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    IF (SELECT p.role FROM agenda_professionals p WHERE p.code = NEW.professional)
       IS DISTINCT FROM (SELECT t.role FROM agenda_types t WHERE t.code = NEW.type_code) THEN
        RAISE EXCEPTION 'agenda: % cannot take an appointment of type %', NEW.professional, NEW.type_code;
    END IF;
    RETURN NEW;
END
$$;
CREATE OR REPLACE TRIGGER agenda_appointments_role
    BEFORE INSERT OR UPDATE OF professional, type_code ON agenda_appointments
    FOR EACH ROW EXECUTE FUNCTION agenda_check_role();

-- --- Internal functions ---------------------------------------------------------------------------

-- G16: HMAC-SHA256('agenda:' || from.id) under the SPEC-006 key; differs from consent_subject.
CREATE OR REPLACE FUNCTION agenda_subject(p_from_id text) RETURNS text
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_key bytea;
BEGIN
    IF p_from_id IS NULL OR p_from_id !~ '^[0-9]{1,20}$' THEN
        RAISE EXCEPTION 'agenda_subject: invalid Telegram user id';
    END IF;
    SELECT k.key INTO v_key FROM consent_key k;
    IF v_key IS NULL THEN
        RAISE EXCEPTION 'agenda_subject: consent key missing';
    END IF;
    RETURN encode(hmac(convert_to('agenda:' || p_from_id, 'UTF8'), v_key, 'sha256'), 'hex');
END
$$;

-- G17: appointments that ended more than 30 days ago. Always the real now(), never a caller's time.
CREATE OR REPLACE FUNCTION agenda_purge() RETURNS void
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    DELETE FROM agenda_appointments WHERE ends_at < now() - interval '30 days';
$$;

-- G6/G10: the slot rules, shared by the lookup and the booking. NULL = valid, else the first reason.
CREATE OR REPLACE FUNCTION agenda_slot_problem(p_type text, p_start timestamptz, p_now timestamptz)
RETURNS text
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    t agenda_types;
    s agenda_settings;
    v_local     timestamp;   -- Madrid wall-clock start
    v_end_local timestamp;   -- Madrid wall-clock end
BEGIN
    SELECT * INTO t FROM agenda_types WHERE code = p_type;
    IF NOT FOUND THEN RETURN 'unknown_type'; END IF;
    IF NOT t.bookable_by_bot THEN RETURN 'request_only'; END IF;
    SELECT * INTO s FROM agenda_settings;

    v_local := p_start AT TIME ZONE 'Europe/Madrid';
    IF extract(second FROM v_local) <> 0
       OR extract(minute FROM v_local)::integer % s.slot_minutes <> 0 THEN
        RETURN 'not_on_grid';
    END IF;
    IF p_start < p_now + s.min_lead THEN RETURN 'too_soon'; END IF;
    IF p_start > p_now + s.horizon THEN RETURN 'too_far'; END IF;
    IF EXISTS (SELECT 1 FROM agenda_closures c WHERE c.day = v_local::date)
       OR NOT EXISTS (SELECT 1 FROM agenda_hours h
                      WHERE h.weekday = extract(isodow FROM v_local)::smallint
                        AND extract(month FROM v_local)::smallint = ANY (h.months)) THEN
        RETURN 'closed';
    END IF;
    v_end_local := (p_start + t.duration) AT TIME ZONE 'Europe/Madrid';
    IF NOT EXISTS (SELECT 1 FROM agenda_hours h
                   WHERE h.weekday = extract(isodow FROM v_local)::smallint
                     AND extract(month FROM v_local)::smallint = ANY (h.months)
                     AND v_local >= v_local::date + h.start_time
                     AND v_end_local <= v_local::date + h.end_time) THEN
        RETURN 'outside_hours';
    END IF;
    RETURN NULL;
END
$$;

-- G5–G8 with an explicit "now" (tests only; n8n calls agenda_free_slots).
CREATE OR REPLACE FUNCTION agenda_free_slots_at(p_type text, p_from timestamptz, p_limit integer,
                                                p_now timestamptz)
RETURNS TABLE (result text, starts_at timestamptz, ends_at timestamptz, professional text)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    t agenda_types;
    s agenda_settings;
BEGIN
    PERFORM agenda_purge();
    SELECT * INTO t FROM agenda_types WHERE code = p_type;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'agenda: unknown appointment type %', p_type;
    END IF;
    IF NOT t.bookable_by_bot THEN
        RETURN QUERY SELECT 'request_only'::text, NULL::timestamptz, NULL::timestamptz, NULL::text;
        RETURN;
    END IF;
    SELECT * INTO s FROM agenda_settings;

    RETURN QUERY
    WITH days AS (
        SELECT d::date AS day
        -- timestamp (not timestamptz) series, so the session TimeZone plays no part
        FROM generate_series((greatest(p_from, p_now + s.min_lead) AT TIME ZONE 'Europe/Madrid')::date::timestamp,
                             ((p_now + s.horizon) AT TIME ZONE 'Europe/Madrid')::date::timestamp,
                             interval '1 day') AS d
    ), candidates AS (
        SELECT dy.day, h.start_time AS block, (g.local_start AT TIME ZONE 'Europe/Madrid') AS slot_start
        FROM days dy
        JOIN agenda_hours h
          ON h.weekday = extract(isodow FROM dy.day)::smallint
         AND extract(month FROM dy.day)::smallint = ANY (h.months)
        CROSS JOIN LATERAL generate_series(dy.day + h.start_time, dy.day + h.end_time - t.duration,
                                           make_interval(mins => s.slot_minutes)) AS g(local_start)
        WHERE NOT EXISTS (SELECT 1 FROM agenda_closures c WHERE c.day = dy.day)
    ), free AS (
        SELECT c.day, c.block, c.slot_start, pro.code AS pro_code
        FROM candidates c
        CROSS JOIN LATERAL (
            SELECT p.code FROM agenda_professionals p
            WHERE p.role = t.role
              AND NOT EXISTS (SELECT 1 FROM agenda_appointments a
                              WHERE a.professional = p.code AND a.status = 'booked'
                                AND a.during && tstzrange(c.slot_start, c.slot_start + t.duration, '[)'))
            ORDER BY p.code LIMIT 1
        ) pro
        WHERE c.slot_start >= p_from
          AND agenda_slot_problem(p_type, c.slot_start, p_now) IS NULL
          AND EXISTS (SELECT 1 FROM agenda_rooms r
                      WHERE NOT EXISTS (SELECT 1 FROM agenda_appointments a
                                        WHERE a.room = r.code AND a.status = 'booked'
                                          AND a.during && tstzrange(c.slot_start, c.slot_start + t.duration, '[)')))
    ), one_per_block AS (
        SELECT DISTINCT ON (f.day, f.block) f.slot_start, f.pro_code
        FROM free f
        ORDER BY f.day, f.block, f.slot_start
    )
    SELECT 'free'::text, o.slot_start, o.slot_start + t.duration, o.pro_code
    FROM one_per_block o
    ORDER BY o.slot_start
    LIMIT p_limit;
END
$$;

-- G9–G13, G10b with an explicit "now" (tests only; n8n calls agenda_book).
CREATE OR REPLACE FUNCTION agenda_book_at(p_type text, p_start timestamptz, p_from_id text,
                                          p_now timestamptz)
RETURNS TABLE (result text, reason text, appointment_id uuid, starts_at timestamptz,
               ends_at timestamptz, professional text, room text)
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    t agenda_types;
    s agenda_settings;
    v_problem text;
    v_subject text;
    v_end     timestamptz;
    v_id      uuid;
    pro       record;
    rm        record;
BEGIN
    PERFORM agenda_purge();
    v_problem := agenda_slot_problem(p_type, p_start, p_now);
    IF v_problem IS NOT NULL THEN
        RETURN QUERY SELECT 'invalid'::text, v_problem, NULL::uuid, NULL::timestamptz, NULL::timestamptz,
                            NULL::text, NULL::text;
        RETURN;
    END IF;
    SELECT * INTO t FROM agenda_types WHERE code = p_type;
    SELECT * INTO s FROM agenda_settings;
    v_subject := agenda_subject(p_from_id);

    -- G10b: serialize bookings of the same subject, then count its future bot appointments.
    PERFORM pg_advisory_xact_lock(hashtextextended('agenda:' || v_subject, 0));
    IF (SELECT count(*) FROM agenda_appointments a
        WHERE a.subject = v_subject AND a.status = 'booked' AND a.channel = 'telegram'
          AND a.starts_at > p_now) >= s.max_future_per_subject THEN
        RETURN QUERY SELECT 'limit'::text, NULL::text, NULL::uuid, NULL::timestamptz, NULL::timestamptz,
                            NULL::text, NULL::text;
        RETURN;
    END IF;

    -- G12/G13: the exclusion constraints decide; a lost race only moves on to the next combination.
    v_end := p_start + t.duration;
    FOR pro IN SELECT p.code FROM agenda_professionals p WHERE p.role = t.role ORDER BY p.code LOOP
        FOR rm IN SELECT r.code FROM agenda_rooms r ORDER BY r.code LOOP
            BEGIN
                INSERT INTO agenda_appointments AS a (subject, type_code, starts_at, ends_at, professional, room)
                VALUES (v_subject, p_type, p_start, v_end, pro.code, rm.code)
                RETURNING a.id INTO v_id;
                RETURN QUERY SELECT 'booked'::text, NULL::text, v_id, p_start, v_end, pro.code, rm.code;
                RETURN;
            EXCEPTION WHEN exclusion_violation THEN
                NULL;  -- this professional or this room is busy at that time: try the next pair
            END;
        END LOOP;
    END LOOP;
    RETURN QUERY SELECT 'taken'::text, NULL::text, NULL::uuid, NULL::timestamptz, NULL::timestamptz,
                        NULL::text, NULL::text;
END
$$;

-- --- Public functions (what n8n will call): no time parameter, always now() -----------------------

CREATE OR REPLACE FUNCTION agenda_free_slots(p_type text, p_from timestamptz, p_limit integer DEFAULT 3)
RETURNS TABLE (result text, starts_at timestamptz, ends_at timestamptz, professional text)
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    SELECT * FROM agenda_free_slots_at(p_type, p_from, p_limit, now());
$$;

CREATE OR REPLACE FUNCTION agenda_book(p_type text, p_start timestamptz, p_from_id text)
RETURNS TABLE (result text, reason text, appointment_id uuid, starts_at timestamptz,
               ends_at timestamptz, professional text, room text)
LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    SELECT * FROM agenda_book_at(p_type, p_start, p_from_id, now());
$$;
