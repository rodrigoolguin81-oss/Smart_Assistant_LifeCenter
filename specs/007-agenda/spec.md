---
type: spec
spec_id: SPEC-004
title: agenda — Functional Spec
description: Requirements for the project's own appointment agenda in Neon (RES-01) — opening hours, professionals with roles, rooms, appointment types, the free-slot lookup, a booking primitive with no double booking (NFR-07, R-05), a pseudonymous subject and 30-day retention — in EARS notation, with no patient-facing flow and no n8n change.
tags: [spec, agenda, SPEC-004, RES-01, RF-005, NFR-07, R-05, CONF-001, DEP-03]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md, ../../docs/01-charter.md, ../../kb/horario-clinica.md, ../../kb/tarifas-generales.md, ../006-consent/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# agenda — Specification

Traceability: PRD `docs/03-prd.md` §6 (RES-01), §5.1 (RF-005, availability and the booking
primitive only), §5.2 (NFR-07), §8 (R-05), §9 (DEP-03), §10 (CONF-001, option a), §11
(**SPEC-004**); charter §4, §7. It uses the SPEC-006 consent key
(`specs/006-consent/`). Decisions in [clarifications](./clarifications.md).

## Context

Para pedir cita por Telegram (US-004), el bot necesita una agenda donde mirar huecos libres y
apuntar citas sin tocar el software de la clínica (RES-01). Esta spec construye solo esa agenda
en Neon:

- el horario, los profesionales con su rol, los gabinetes y los tipos de cita;
- la búsqueda de huecos;
- una función de reserva que nunca da el mismo hueco dos veces.

Nadie la usa todavía desde Telegram. Reservar, mover, cancelar y los recordatorios vendrán en
specs posteriores, que llamarán a estas funciones.

**Definitions.**

- *Role*: `dentist` or `hygienist`.
- *Professional*: a person with exactly one role. The example staff is «Odontóloga 1» and
  «Odontólogo 2» (dentists) and «Higienista» (hygienist).
- *Room*: a treatment room. The example rooms are «Gabinete 1», «Gabinete 2» and «Gabinete 3».
- *Appointment type*: a code, a name, a duration, the role it needs and whether the bot may book
  it. The example types:

  | Code | Name | Duration | Role | Bookable by the bot |
  |---|---|---|---|---|
  | `revision` | Revisión | 30 min | dentist | yes |
  | `limpieza` | Limpieza | 45 min | hygienist | yes |
  | `primera_visita` | Primera visita | 30 min | dentist | yes |
  | `blanqueamiento` | Blanqueamiento | 90 min | dentist | no (request only) |
  | `tratamiento_largo` | Implantes, ortodoncia u otro tratamiento largo | — | dentist | no (request only) |

- *Opening block*: a weekday with a start and an end time. The example blocks are the same as
  HOR-001: Monday to Friday 9:00–14:00 and 16:00–20:00, and Saturday 10:00–14:00. There are none
  on Sunday.
- *Closure*: a date on which the clinic is closed (holidays). There are none until LifeCenter
  provides its calendar.
- *Slot*: a start time on the 15-minute grid. The whole appointment must fit inside one opening
  block of a day that is not a closure.
- *Booking window*: from 2 hours after the current time to 30 days after it.
- *Free slot* for a type: a slot inside the booking window for which at least one professional
  with the type's role and at least one room have no `booked` appointment overlapping it.
- *Subject*: `HMAC-SHA256('agenda:' || from.id, consent key)`, in hex. The key is SPEC-006's,
  but the prefix is different, so an agenda subject never equals a consent subject.
- *Appointment*: a row with the subject, type, start, end, professional, room, status (`booked`
  or `cancelled`), channel and creation time.
- *Example value*: a configuration value marked `ejemplo` until LifeCenter confirms it (DEP-01,
  DEP-03).

All times are Europe/Madrid wall-clock times, stored as `timestamptz` (clarifications A1).

## Requirements (EARS)

### Configuration (clarifications Q2–Q4, Q11, Q13)

- G1. The agenda SHALL hold its configuration in its own Neon tables: opening blocks, closures,
  professionals with their role, rooms and appointment types. It SHALL NOT read or write
  LifeCenter's clinical software (RES-01).
- G2. The schema step SHALL seed `main` with the example configuration of the Definitions, every
  row marked as example, and with **no appointments**.
- G3. Every appointment type SHALL state the role it needs. A professional SHALL be assigned
  only to types of their own role (clarifications Q3).
- G4. The agenda's opening blocks SHALL equal the hours stated in HOR-001
  (`kb/horario-clinica.md`). A test SHALL fail when they differ.

### Free slots (US-004, clarifications Q5, Q6)

- G5. `agenda_free_slots(type, from, limit)` SHALL return up to `limit` free slots for the type,
  3 by default. They SHALL start at or after `from`, be **earliest first**, and include **at most
  one per opening block**. Each slot SHALL come with the professional who would take it.
- G6. A returned slot SHALL be on the 15-minute grid, fit entirely inside one opening block, not
  fall on a closure, lie inside the booking window, and be free.
- G7. IF the type is not bookable by the bot, THEN `agenda_free_slots` SHALL return no slots
  and SHALL say so (`request_only`). That is the CONF-001 option (a) rule.
- G8. IF the type does not exist, THEN `agenda_free_slots` SHALL fail with a clear error.

### Booking primitive (RF-005 create, NFR-07, R-05, clarifications Q7)

- G9. `agenda_book(type, start, from_id)` SHALL create one `booked` appointment. It SHALL use a
  professional of the type's role and a room, both free for the whole duration, and return it.
- G10. `agenda_book` SHALL apply **the same slot rules as `agenda_free_slots`** (G6, G7). IF
  the start time is not valid, THEN `agenda_book` SHALL create nothing and SHALL return
  `invalid` with one of these reasons (human, 2026-11-22):
  - outside the opening hours;
  - crossing the midday break, or the end of an opening block;
  - on a closure date;
  - not aligned to the 15-minute grid;
  - less than 2 hours after the current time;
  - more than 30 days after it;
  - the type is not bookable by the bot (`request_only`).
- G10b. IF the subject already has **one future `booked` appointment booked by the bot**, THEN
  `agenda_book` SHALL create nothing and SHALL return `limit`. This SHALL hold even when two
  bookings for the same subject run at the same time (human, 2026-11-22; clarifications Q14).
  The limit is an example value.
- G11. IF no professional of the role or no room is free for the slot, THEN `agenda_book` SHALL
  create nothing and SHALL return `taken`.
- G12. The database SHALL make two `booked` appointments impossible for the same professional,
  or for the same room, at overlapping times. It SHALL do so with exclusion constraints, so this
  holds whatever the caller does.
- G13. WHEN several bookings of the same slot run at the same time, exactly as many SHALL
  succeed as there are free professionals of the role and free rooms, and the rest SHALL return
  `taken` without an unhandled error.
- G14. This spec SHALL NOT expose booking to patients. It SHALL NOT ask for confirmation and
  SHALL NOT check consent, because there is no patient-facing caller yet. The booking spec SHALL
  add both: confirmation (RF-005) and consent in force (SPEC-006).

### Patient data, pseudonymization and retention (clarifications Q8, Q9)

- G15. An appointment SHALL hold, about the patient, only the subject, plus the type and the
  times. The professional, room, status, channel and creation time are agenda data. It SHALL
  hold no name, phone, chat id, Telegram id, username or free text.
- G16. The subject SHALL be computed in Postgres from `from_id` passed as a parameter, with the
  SPEC-006 key. The `from_id` SHALL NOT be stored, and the key SHALL be neither copied, printed
  nor regenerated. No new key table SHALL be created.
- G17. An appointment SHALL be deleted once its end is more than 30 days in the past. The
  deletion SHALL run inside the agenda functions, as in SPEC-006, with no scheduled workflow.

### Code, tests and deployment (clarifications Q10, Q12)

- G18. The agenda's tables, constraints, seed and functions SHALL live in
  `app/infra/sql/003_agenda.sql`. The script SHALL be idempotent, be applied by
  `app/infra/schema.py`, and SHALL NOT modify `kb_fragments`, `consent` or `consent_key`.
- G19. Tests SHALL be written before the SQL and run with pytest against the **Neon test branch
  only**. They SHALL include the NFR-07 test: **10 concurrent bookings of the same slot**, of a
  type whose role has exactly one free professional, give exactly **1** success and **9**
  `taken`.
- G20. The schema SHALL be applied to `main` only after the human confirms, with a read-only
  check before and after. The check SHALL show that `kb_fragments` and `consent` are unchanged
  and that the configuration rows are present.
- G21. The first task SHALL check the host behind each Neon credential that the work uses
  (AGENTS.md "Preflight check").
- G22. This spec SHALL NOT change n8n (RES-03).
- G23. The README SHALL describe the agenda, where each example value is changed, and a
  read-only query for reception to see the day's appointments. The reception panel itself is
  RF-007.

## Acceptance criteria

- [ ] On the test branch, `agenda_free_slots('limpieza', …)` returns at most 3 slots, earliest
  first, one per opening block, all on the grid, within opening hours and the booking window,
  and taken by the hygienist.
- [ ] With synthetic appointments filling the hygienist's morning, the next slot offered for
  `limpieza` is in a later block, while `revision` still finds a dentist that morning.
- [ ] A 45-minute `limpieza` is never offered at 13:30, nor on a Sunday, nor on a closure date.
  A slot less than 2 hours ahead, or more than 30 days ahead, is never offered.
- [ ] `agenda_free_slots('blanqueamiento', …)` returns no slots and `request_only`.
- [ ] NFR-07: 10 concurrent `agenda_book('limpieza', same start, different fake ids)` give
  exactly 1 `booked` and 9 `taken`. A direct `INSERT` of an overlapping appointment for the
  same professional or room is rejected by the database.
- [ ] With 2 dentists, 2 concurrent bookings of the same `revision` slot both succeed with
  different dentists and rooms, and a third gets `taken`.
- [ ] `agenda_book` returns `invalid`, with the matching reason and no row created, for a start:
  - outside the opening hours (8:45, 20:00, a Sunday);
  - crossing the break or the end of a block (a 45-minute `limpieza` at 13:30, or at 19:30);
  - on a closure date;
  - off the grid (9:10);
  - less than 2 hours ahead;
  - more than 30 days ahead.

  It returns `invalid` with `request_only` for `blanqueamiento`.
- [ ] A subject with one future appointment booked by the bot gets `limit`, and nothing is
  created, on a second booking, whatever the type or slot. Two concurrent bookings for the same
  subject at different free slots give 1 `booked` and 1 `limit`. Once the first appointment is
  in the past, the subject can book again.
- [ ] **Daylight saving time** (Europe/Madrid changes on the last Sunday of March and of
  October; in 2026, 29 March and 25 October): in both weeks, the slots offered and the
  appointments booked keep Madrid local time.
  - The first slot on the Friday before and on the Monday after is 9:00 local.
  - A `limpieza` booked at 9:00 local on each of those days starts at 9:00 and ends at 9:45
    local.
  - The stored UTC offset changes from `+01` to `+02` in March, and from `+02` to `+01` in
    October.
- [ ] An appointment row holds no `from_id`, chat id or name. Its subject is 64 hex characters
  and differs from the SPEC-006 consent subject of the same id.
- [ ] An appointment that ended 31 days ago is removed by the next agenda call; one that ended 29
  days ago remains.
- [ ] The opening blocks equal HOR-001 (the consistency test passes).
- [ ] Re-applying the schema changes neither `kb_fragments`, nor `consent`, nor the key in
  `consent_key`.
- [ ] On `main`, after the human confirms: the configuration rows are there, there are 0
  appointments, and `kb_fragments` and `consent` are unchanged (row counts and md5).

## Known limitations

- **The appointment type is health data**: "limpieza on day X" reveals that the person is a
  patient and of what kind.
  - It is necessary for the service and kept 30 days.
  - It is pseudonymized by the subject, but not anonymous.
  - Accepted for the demo with test accounts only, pending DEP-04.
- **Reception cannot tell who is coming.** The agenda holds no name or phone, so a real clinic
  could not use it as is. The reception panel spec decides how patients are identified.
- **No chat id**, so this agenda alone cannot send reminders. The reminders spec decides this,
  with its own consent (CONF-005) and a separate table.
- **Example data everywhere**: hours, staff, durations, booking window and holidays (empty).
  Opening to real patients stays blocked, now also on DEP-03.
- **The key is in the same database** as the subjects, as in SPEC-006.

## Out of scope

- Every patient-facing flow, each in a later spec:
  - booking from Telegram, with buttons, confirmation, `offer_booking` and requests for
    non-bookable types (proposed SPEC-007);
  - moving and cancelling (US-005), including what happens to future appointments when consent
    is withdrawn (proposed SPEC-008);
  - reminders (RF-006, US-006, CONF-005), including the chat id table (proposed SPEC-009).
- The reception panel and how it identifies patients (RF-007).
- Individual schedules, holidays and breaks per professional, buffers between appointments, and
  several clinics (DEP-03; PRD §7).
- Synchronization with LifeCenter's agenda software (RES-01; charter §3, §8).
- Any change to n8n, to the consent tables or to the knowledge base.
