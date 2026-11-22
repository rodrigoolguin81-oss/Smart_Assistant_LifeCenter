---
type: plan
spec_id: SPEC-004
title: agenda — Technical Plan
description: How to build the project's own agenda in Neon — preflight host check, the SQL tests first, the tables, exclusion constraints, seed and functions in 003_agenda.sql on the test branch, then main after confirmation, and the README.
tags: [plan, agenda, SPEC-004, neon]
status: verified
sources: [./spec.md, ./clarifications.md, ../006-consent/plan.md, ../../app/infra/sql/002_consent.sql]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# agenda — Plan

Same pattern as SPEC-006 K2–K3. Everything lives in Neon, with no n8n change (G22):

1. A read-only preflight.
2. The SQL tests, written first.
3. The SQL itself, on the test branch, **only after the human confirms**.
4. `main`, **only after the human confirms**.
5. Docs.

## Architecture

```text
Neon (eu-central-1) — app/infra/sql/003_agenda.sql (idempotent, applied by app/infra/schema.py)

  configuration (seeded, every row marked ejemplo)
    agenda_settings      one row: slot grid 15 min, lead 2 h, horizon 30 days, 1 future per subject
    agenda_hours         weekday (ISO 1–7), start, end, months    — must equal HOR-001 (G4, Q15)
    agenda_closures      date, reason                             — empty
    agenda_professionals code, name, role (dentist | hygienist)
    agenda_rooms         code, name
    agenda_types         code, name, duration, role, bookable_by_bot

  data
    agenda_appointments  id, subject, type, starts_at, ends_at, professional, room,
                         status (booked | cancelled), channel (telegram), created_at,
                         during = tstzrange(starts_at, ends_at)  (generated)
                         EXCLUDE (professional =, during &&) WHERE status = 'booked'
                         EXCLUDE (room =,         during &&) WHERE status = 'booked'

  functions (called later by n8n; today only by the tests)
    agenda_subject(from_id)                      HMAC('agenda:'||from_id, consent_key)   (internal)
    agenda_purge()                               ends_at < now() - 30 days               (internal)
    agenda_slot_problem(type, start, now)        the G6/G10 rules, shared                 (internal)
    agenda_free_slots(type, from, limit)         public: calls agenda_free_slots_at(…, now())
    agenda_book(type, start, from_id)            public: calls agenda_book_at(…, now())
    agenda_free_slots_at(type, from, limit, now) internal, tests only → rows (result, starts_at,
                                                        ends_at, professional)
    agenda_book_at(type, start, from_id, now)    internal, tests only → row (result, reason, id,
                                                        starts_at, ends_at, professional, room)
```

## Step 0: Preflight, read-only (G21, AGENTS.md)

Nothing is created or changed in this step.

- **Hosts:** print only the host of `DIRECT_URL` and of `TEST_DATABASE_URL`, read from `.env`.
  They must differ. Confirm with `current_setting('neon.branch_id')` that they are two different
  branches of the same project (as `tests/infra/test_test_branch.py` does).
- **n8n credential:** this spec uses no n8n credential (G22). Record that `Neon main` was last
  verified to point to `main` in SPEC-006 K5 (a write that was read back from `main`). It is not
  re-verified, because doing so would need a write.
- **Extensions:** check that `btree_gist` is available on both branches, and whether it is
  installed. `pgcrypto` is already installed (SPEC-006 K3).
- **Free names:** no table or function called `agenda_*` exists yet. `consent_key` has 1 row on
  both branches.
- **Time zone:** Europe/Madrid is known to the server (`pg_timezone_names`), and the 2026
  daylight-saving dates are 29 March and 25 October.

## Step 1: The tests, written first (G19)

**`tests/infra/test_agenda_sql.py`** runs against `TEST_DATABASE_URL` only (the existing
`conftest.py` refuses `main`).

**Isolation:**

- fake ids `900101…`;
- every synthetic appointment and closure is removed before and after each test;
- a fixed `p_now`, so results do not depend on the day the tests run. The tests call the
  **internal** functions `agenda_free_slots_at` and `agenda_book_at` with it. The public
  `agenda_free_slots` and `agenda_book` take no time parameter and always use `now()` (human,
  2026-11-22).

**Tests**, one or more per acceptance criterion:

- free slots for `limpieza`: at most 3, earliest first, one per opening block, on the grid,
  inside the hours and the window, all for the hygienist;
- the hygienist's morning filled with synthetic appointments: `limpieza` moves to a later block,
  while `revision` still gets a dentist that morning;
- the edges of the window and the rules: 13:30 for 45 minutes, 19:30, Sunday, a closure (added
  and removed by the test), less than 2 h ahead, more than 30 days ahead;
- `blanqueamiento` → `request_only`; an unknown type → an error;
- `agenda_book` → `invalid` with each reason of G10, and no row created;
- **NFR-07:** 10 threads, each with its own connection and released together by a barrier, book
  `limpieza` at the same start with 10 fake ids → exactly 1 `booked` and 9 `taken`, and 1 row;
- 2 concurrent `revision` bookings at the same start → both `booked`, with different dentists
  and rooms; a third → `taken`;
- a direct overlapping `INSERT` for the same professional, or for the same room →
  `ExclusionViolation`;
- **limit (G10b):**
  - a second booking for the same subject → `limit`;
  - 2 concurrent bookings for the same subject at different free slots → 1 `booked` and 1
    `limit`;
  - with `p_now` after the first appointment, booking again works;
- **subject:**
  - 64 hex characters, not the id;
  - different from `consent_subject(id)` for the same id;
  - stable across a re-applied schema;
- **retention:** a synthetic appointment that ended 31 days ago (by real `now()`) is gone after
  the next call; one that ended 29 days ago remains;
- **what is stored:** the columns of `agenda_appointments` are exactly the planned ones, and no
  row contains the fake id;
- **daylight saving time:**
  - with `p_now` on the Thursday before each change (26 March and 22 October 2026), the first
    `revision` slot on the Friday and on the Monday is 9:00 Europe/Madrid;
  - a `limpieza` booked at 9:00 local on each of those days ends at 9:45 local;
  - the UTC offset is `+01` before and `+02` after in March, and the other way round in
    October;
- **session time zone (found in E0):** the same free slots and the same booked times result
  with the session `TimeZone` set to `GMT` and to `America/New_York`;
- **public signatures (human, 2026-11-22):**
  - `agenda_free_slots` and `agenda_book` have **no** `p_now` parameter, which the test checks
    in `pg_proc`/`pg_get_function_arguments`;
  - each public function returns the same as its `_at` version called with the current time;
- **HOR-001 consistency (G4):**
  - the test parses `kb/horario-clinica.md`: «de lunes a viernes de 9:00 a 14:00 y de 16:00 a
    20:00», «Los sábados … de 10:00 a 14:00», and Sundays closed;
  - it compares them with `agenda_hours`;
  - it fails, with a clear message, if the text cannot be parsed;
- **re-applying the schema** changes neither the `kb_fragments` md5, nor the count of `consent`,
  nor `consent_subject('900101')`.

## Step 2: `003_agenda.sql` on the test branch [asks for confirmation first]

**Extensions and settings:**

- `CREATE EXTENSION IF NOT EXISTS btree_gist`;
- `agenda_settings`: a single row like `consent_key`'s, with `slot_minutes 15`, `min_lead 2
  hours`, `horizon 30 days`, `max_future_per_subject 1` and `ejemplo true`.

**Configuration tables:**

- `agenda_hours`: primary key (weekday, start time), with `start < end`, and `months smallint[]
  NOT NULL`, each value between 1 and 12 (Q15). The seed:
  - Monday–Friday 9:00–14:00, months 1–12;
  - Monday–Friday 16:00–20:00, months 1–7 and 9–12 (no August afternoons);
  - Saturday 10:00–14:00, months 1–12 (the Q15 interpretation);
- `agenda_closures (day date PRIMARY KEY, reason text)`;
- `agenda_professionals (code PRIMARY KEY, name, role CHECK IN ('dentist', 'hygienist'),
  ejemplo)`;
- `agenda_rooms (code PRIMARY KEY, name, ejemplo)`;
- `agenda_types (code PRIMARY KEY, name, duration interval, role, bookable_by_bot, ejemplo)`.
  A bookable type must have a duration.

**Seed:** `INSERT … ON CONFLICT DO NOTHING`, so a re-run never overwrites values the clinic
has changed. Values, all marked as example:

- the spec's types;
- «Odontóloga 1» and «Odontólogo 2» (`dentist`), and «Higienista» (`hygienist`);
- «Gabinete 1–3»;
- the HOR-001 blocks.

**`agenda_appointments`:**

- `id uuid DEFAULT gen_random_uuid()`;
- `subject text CHECK (~ '^[0-9a-f]{64}$')`;
- `type_code`, `professional` and `room` as foreign keys;
- `starts_at` and `ends_at` (`timestamptz`), with `starts_at < ends_at`;
- `status` (`booked` / `cancelled`), `channel` (`telegram`) and `created_at`;
- `during tstzrange GENERATED ALWAYS AS (tstzrange(starts_at, ends_at, '[)')) STORED`;
- the two exclusion constraints (G12);
- an index on `subject`.

**Functions** (`plpgsql`, `SET search_path = public, pg_temp`):

- **`agenda_subject(p_from_id)`:** the same id validation as `consent_subject`, then
  `encode(hmac(convert_to('agenda:' || p_from_id, 'UTF8'), key, 'sha256'), 'hex')` with the key
  from `consent_key`.
- **`agenda_purge()`:** deletes appointments with `ends_at < now() - interval '30 days'`.
  - It always uses the real `now()`, never `p_now`, so a caller cannot purge early.
  - It runs at the start of `agenda_free_slots` and `agenda_book`.
- **`agenda_slot_problem(type, start, now)`:** returns `NULL` when valid, otherwise the first
  reason found, in this order: `unknown_type`, `request_only`, `not_on_grid`, `too_soon`,
  `too_far`, `closed` (closure date, or no block that weekday in that month), `outside_hours` (the start, or the
  start plus the duration, falls outside one single block).
  - The check is done in Madrid local time:
    `local = start AT TIME ZONE 'Europe/Madrid'`; on the grid when the local minute is a
    multiple of 15 and the seconds are 0; and both `local::time` and `(local + duration)::time`
    lie in the same block on `local::date`.
  - It is shared by both public functions, so their rules cannot drift (G10).
- **Public vs internal (human, 2026-11-22).** The functions n8n will call take **no** time
  parameter: `agenda_free_slots(p_type, p_from, p_limit DEFAULT 3)` and `agenda_book(p_type,
  p_start, p_from_id)`. Each is a one-line wrapper that calls its internal `_at` version with
  `now()`.
  - Only the tests call the `_at` versions with a fixed time.
  - Later specs (n8n) must call the public ones.
  - The same database role can technically call either; that is accepted, like the key in the
    same database.
- **`agenda_free_slots_at(p_type, p_from, p_limit, p_now)`** (internal):
  - An unknown type raises an exception (G8). `request_only` returns one row with that result
    and no times (G7).
  - Otherwise it generates candidates: the days from `greatest(p_from, p_now + lead)` to
    `p_now + horizon`, joined to `agenda_hours` by ISO weekday **and by month** (`extract(month
    from local date) = ANY(months)`). Each block becomes
    `generate_series(block start, block end − duration, 15 min)` in local time, converted with
    `(date + time) AT TIME ZONE 'Europe/Madrid'`, which is how daylight saving time is handled.
  - It keeps the candidates where `agenda_slot_problem` is `NULL` and a professional of the
    role (lowest code first) and a room are free.
  - It takes the first one per (date, block) and returns them ordered and limited.
- **`agenda_book_at(p_type, p_start, p_from_id, p_now)`** (internal):
  1. Purge, then `agenda_slot_problem` → `invalid` with the reason.
  2. Compute the subject, then take `pg_advisory_xact_lock` on a hash of it, which serializes
     concurrent bookings of the same subject (G10b). Count that subject's `booked`,
     `telegram`-channel appointments with `starts_at > p_now`: at the limit → `limit`.
  3. For each free professional of the role, then each free room, try the `INSERT`. On
     `exclusion_violation`, which means another transaction won it, try the next combination.
     None left → `taken` (G11, G13).

  The constraint is what guarantees no double booking (G12). The loop only turns a lost race
  into `taken`.

**Run order, after the human confirms:**

1. the tests, red: the ones that apply the schema are excluded, so nothing is created;
2. `python -m app.infra.schema --database-url-env TEST_DATABASE_URL`;
3. the tests, green;
4. all of `tests/infra`, so SPEC-002 and SPEC-006 still pass.

## Step 3: `main` [asks for confirmation first] (G20)

Read-only check before, then `python -m app.infra.schema --database-url-env DIRECT_URL`, then
the same check after. The check prints only counts, existence and digests:

- `kb_fragments`: rows and md5 (must not change);
- `consent`: row count (must not change);
- `consent_key`: still 1 row. The key is never printed: the check compares
  `consent_subject('900101')` before and after, inside the script;
- the `agenda_*` tables and their row counts: 2 + 1 professionals, 3 rooms, 5 types, 5 + 5 + 1
  hour blocks (the afternoon ones without August), 0 closures, 0 appointments, 1 settings row;
- the 7 functions and `btree_gist`.

## Step 4: Docs (G23)

- README, a new "Agenda" subsection:
  - what it is (no patient flow yet);
  - where each example value is changed: the `agenda_*` tables and `agenda_settings`, keeping
    `agenda_hours` equal to HOR-001;
  - how to apply the schema;
  - reception's read-only query for a day's appointments (type, time, professional, room; the
    subject is not shown);
  - the limitations.
- `specs/index.md`.

## Requirement → component map

| Requirement | Component |
|---|---|
| G1–G3 | configuration tables, seed, role check (Step 2) |
| G4 | `agenda_hours.months` (Q15); HOR-001 consistency test, month by month, and the August test (Step 1) |
| G5–G8 | `agenda_free_slots` → `agenda_free_slots_at`, `agenda_slot_problem` |
| G9–G11, G10b | `agenda_book` → `agenda_book_at`, advisory lock per subject |
| G12, G13 | exclusion constraints; NFR-07 concurrency test |
| G14 | no patient-facing caller; consent and confirmation left to the booking spec |
| G15–G17 | `agenda_appointments` columns, `agenda_subject`, `agenda_purge` |
| G18–G20 | `003_agenda.sql`, `test_agenda_sql.py`, Steps 2–3 |
| G21 | Step 0 |
| G22 | no n8n change |
| G23 | Step 4 |
