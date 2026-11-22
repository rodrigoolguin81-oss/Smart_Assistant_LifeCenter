---
type: clarifications
spec_id: SPEC-004
title: agenda — Clarifications
description: Questions resolved with the human before writing SPEC-004 (the project's own appointment agenda in Neon, RES-01) — what the PRD and the charter say about appointments, what this spec covers, and what it leaves for later specs (booking, moving, cancelling, reminders).
tags: [clarify, agenda, SPEC-004, RES-01, RF-005, NFR-07, R-05, CONF-001, DEP-03]
status: verified
sources: [../../docs/03-prd.md, ../../docs/01-charter.md, ../../kb/horario-clinica.md, ../../kb/tarifas-generales.md, ../002-answer-generation/clarifications.md, ../006-consent/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# agenda — Clarifications

The human answered every question on 2026-11-22 (see **Decisions**). The questions are kept below
as they were asked, each with the agent's proposal. **Where a decision differs from a proposal,
the decision prevails.**

The PRD's traceability (§11) assigns appointments to **SPEC-004**. This folder is `007-agenda`
because 004–006 are already taken. The `spec_id` is SPEC-004 (see Q1).

## What the PRD and the charter say

**Restriction and dependency:**

- **RES-01 (PRD §6):** the bot never writes to LifeCenter's clinical management software. In
  v1.0 it works on an agenda of the project's own (source: Rossana Riquelme).
- **Charter §7:** "Para el PoC basta con una agenda propia del proyecto, sin tocar el software
  de gestión clínica."
- **Charter §8:** it is not yet known which agenda software LifeCenter uses, or whether it has an
  API for integrating it after the PoC.
- **Charter §3 (out of scope):** changes to and integrations with the clinical management
  software in production.
- **DEP-03 (PRD §9):** the duration of each treatment and each professional's schedule are still
  to be defined, and the agenda is built from them.

**Requirements and stories:**

- **RF-005:** look up availability and create, move or cancel appointments, asking the patient
  for explicit confirmation before writing to the agenda.
- **US-004** (book a free slot): up to 3 slots offered with buttons. After the patient picks one,
  the bot repeats date, time and treatment, and creates the appointment only when the patient
  confirms.
- **US-005** (move or cancel): the patient has a future appointment "asociada a su cuenta de
  Telegram". The bot shows it, asks for confirmation, and frees the slot.
- **RF-006 / US-006** (reminders): a reminder 24 h before, with date, time and address, and
  buttons to confirm or cancel. Depends on CONF-005.
- **NFR-07:** 0 double bookings with 10 simultaneous requests on the same slot. Verified by a
  concurrency test on the agenda service.
- **R-05:** double booking of the same slot (medium impact, low probability). Mitigation: a
  transaction that locks the row in the agenda, plus the NFR-07 test.
- **CONF-001** (open, **blocks RF-005**):
  - the director wants the bot to book everything;
  - the dentist wants to validate first visits for long treatments (implants, orthodontics);
  - the proposal is option (a): the bot books check-ups, cleanings and first visits, and only
    *requests* the rest.
- **CONF-005:** consent before receiving proactive messages (reminders). It is now covered for
  conversations by SPEC-006; reminders were left to RF-006.
- **US-001 / SPEC-001 Q14:** after a price or treatment answer the bot should offer to book.
  SPEC-001 defined an `offer_booking` flag for that, but the n8n demo workflows do not return or
  use it today: neither export contains `offer_booking`.

**Out of scope (PRD §7, charter §3):** no clinical history, and payments, quotes and commercial
campaigns.

**Targets (PRD §2, charter §5):**

- at least 20 % of appointments created by the bot by the end of the pilot;
- at least 20 % fewer no-shows with reminders active;
- about 250 appointments a month, about 12 per working day, and 10 % no-shows (estimates, PRD §1).

**The clinic (PRD §1):** 2 dentists, 1 hygienist and 3 treatment rooms (*gabinetes*).

## Facts found before asking (agent, 2026-11-22)

- **Opening hours in the knowledge base**, `kb/horario-clinica.md` (HOR-001, `ejemplo: true`):
  - Monday to Friday 9:00–14:00 and 16:00–20:00;
  - Saturday 10:00–14:00;
  - closed on Sundays and holidays.

  These are example data until DEP-01.
- **Durations in the knowledge base**, `kb/tarifas-generales.md` (TAR-001, `ejemplo: true`):
  - cleaning: about 45 min, done by the hygienist;
  - whitening: one 90-minute session plus a check-up a month later;
  - first visit: free, done by the dentist, with no duration given.

  Nothing else has a duration. DEP-03 is pending.
- **Neon already holds** `kb_fragments` and the SPEC-006 consent tables, with an HMAC key in
  `consent_key` that **must never be regenerated** (SPEC-006, Known limitations).
- **AGENTS.md "Preflight check"** applies: this spec touches Neon, so its first task must check
  the **host** behind each credential, not only the user.
- **RES-03** (channel independence): the agenda must not depend on Telegram or on n8n.

## Coverage

**Proposed for this spec (SPEC-004, the agenda base):**

- RES-01: the project's own agenda in Neon, with no link to the clinic's software;
- the data model behind RF-005:
  - opening hours;
  - professionals and rooms;
  - appointment types with their duration, and who can do each one;
  - appointments;
- the availability lookup of RF-005 and US-004: up to 3 free slots for a type;
- NFR-07 and R-05: no double booking, guaranteed by the database and proven by a concurrency
  test;
- a booking primitive that the later specs call. It is tested here, but not exposed to patients.

**Left for later specs** (ids are proposals, Q1):

- **Booking from Telegram** (US-004, the create part of RF-005, CONF-001): the dialogue, the 3
  buttons, the confirmation, `offer_booking` after a price, and asking for a treatment type.
- **Moving and cancelling** (US-005, RF-005): finding "my" appointment, confirming, and freeing
  the slot.
- **Reminders** (US-006, RF-006, CONF-005): the scheduled 24 h job, consent for proactive
  messages, and how the bot reaches the patient (it needs a chat id, see Q8).
- **Reception's view of the agenda and the handoffs** (RF-007, panel).

## Decisions (human, 2026-11-22)

- **Q1, Q2, Q5, Q6, Q10, Q11, Q12, Q13:** the proposals are accepted as written.
- **Q3: professionals are not interchangeable.**
  - Each professional has a **role**: `dentist` or `hygienist`.
  - Each appointment type states the role it needs: limpieza → hygienist; revisión and primera
    visita → dentist.
  - There are **2 dentists, 1 hygienist and 3 rooms**, all working the full opening hours until
    DEP-03.
- **Q4: accepted.**
  - Bookable by the bot: revisión 30 min, limpieza 45 min and primera visita 30 min.
  - Request only: blanqueamiento and long treatments.
  - **CONF-001 is resolved with option (a)** for this project.
  - All values are marked as example.
- **Q7: accepted.** Exclusion constraints per professional and per room, with the test of 10
  simultaneous bookings on the Neon test branch.
- **Q8: in this spec an appointment stores only the HMAC subject, the type and the times.**
  - The subject uses the SPEC-006 key with a different prefix.
  - There is no name, phone or chat id. The professional, room, status and timestamps are
    operational fields of the agenda, not patient data.
  - **The chat id for reminders** is decided in the reminders spec, with its own consent
    (CONF-005), in a **separate table**.
  - **How reception identifies a patient** is decided in the reception panel spec.
  - **The appointment type is health data** (it reveals that the person is a patient and of what
    kind). It is **necessary for the service** and kept **30 days** (Q9).
- **Q9: accepted.**
  - Booking will require consent in force.
  - An appointment is deleted 30 days after it ends, by the agenda functions.
  - **The cancelling spec will review what happens to future appointments when consent is
    withdrawn.**
- **A1–A4:** accepted as written.

### Added at spec review (human, 2026-11-22)

- **Q14: Limit per patient.** A subject may have **at most 1 future appointment booked by the
  bot**. If it already has one, `agenda_book` creates nothing and returns a new result, `limit`.
  It is an example value, like the other configuration.
- **Same rules for booking as for the lookup.** `agenda_book` applies the slot rules of
  `agenda_free_slots` and returns `invalid` with the reason when the start is:
  - outside the opening hours;
  - crossing the break;
  - on a holiday;
  - off the 15-minute grid;
  - less than 2 hours ahead, or more than 30 days ahead.
- **Daylight saving time.** An acceptance criterion checks that slots and appointments keep
  Madrid local time in the weeks of the change: the last Sunday of March and the last Sunday of
  October.

## Questions as asked, with the agent's proposals

- **Q1: Id, scope and later specs.**
  - Proposal: `spec_id: SPEC-004`, as in PRD §11, in folder `specs/007-agenda/`.
  - It covers only the agenda base listed above, with no patient-facing flow and no change to
    n8n.
  - Later specs get new ids, proposed as SPEC-007 (booking from Telegram), SPEC-008 (moving and
    cancelling) and SPEC-009 (reminders).
  - PRD §11's row for RF-005 stays "SPEC-004", with those as follow-ups.

- **Q2: Opening hours and holidays: where do they come from?**
  - Proposal: an agenda table `agenda_hours` (weekday, start, end; one or more blocks per day),
    seeded with **the same example values as HOR-001** and marked as example until DEP-01.
  - A test fails if `agenda_hours` and HOR-001 disagree, so the bot never tells a patient one
    schedule and books another. HOR-001 is meant for answers, not for booking, so it is not read
    directly.
  - Holidays go in a table `agenda_closures` (date and reason), **empty** until LifeCenter gives
    its calendar: its location, and so its regional holidays, is not known.
  - Time zone: Europe/Madrid, with every timestamp stored as `timestamptz`, so daylight-saving
    changes are handled.

- **Q3: Professionals and rooms.**
  - Proposal: model both, as in PRD §1: **3 professionals** with neutral example names
    («Odontóloga 1», «Odontólogo 2», «Higienista») and **3 rooms** («Gabinete 1–3»).
  - An appointment takes one professional and one room for its whole duration.
  - Until DEP-03, every professional works the full opening hours: no individual schedules,
    holidays or breaks.
  - With 3 professionals and 3 rooms, rooms never limit availability. They are modelled anyway,
    so that a later schedule or a fourth professional does not need a new model.

- **Q4: Appointment types, durations, and who does each.**
  - Proposal, example values until DEP-03 and Prince Calderon's review:

    | Type | Duration | Professional | Bookable by the bot (CONF-001 a) |
    |---|---|---|---|
    | Revisión | 30 min | a dentist | yes |
    | Limpieza | 45 min (TAR-001) | the hygienist | yes |
    | Primera visita | 30 min | a dentist | yes |
    | Blanqueamiento | 90 min (TAR-001) | a dentist | no: request only |
    | Implantes, ortodoncia, other long treatments | — | a dentist | no: request only (CONF-001) |

  - CONF-001 is applied provisionally with option (a), as with the other open conflicts. This
    spec only stores whether a type can be booked by the bot. What a "request" does is left to
    the booking spec.

- **Q5: Slot grid, gaps and booking window.**
  - Proposal:
    - start times on a **15-minute grid**, with no buffer between appointments;
    - an appointment must fit **inside one opening block**, so it never crosses 14:00–16:00 or
      the closing time;
    - bookable from **2 hours after now** to **30 days ahead**.

    All are example values for the clinic to confirm.

- **Q6: The availability lookup.**
  - Proposal: a database function `agenda_free_slots(type, from, limit)`. It returns up to
    `limit` (3 by default, US-004) free start times, **earliest first**, at most **one per
    half-day**, so the 3 options are not three consecutive quarters of an hour. It also returns
    the professional who would take each one.
  - Turning "la próxima semana" into a date range is for the booking spec.

- **Q7: How double booking is prevented (NFR-07, R-05).**
  - Proposal: in the database itself.
  - **Exclusion constraints** (`btree_gist`) on (professional, time range) and (room, time
    range), applied to appointments that are not cancelled.
  - A function `agenda_book(type, start, subject)` picks a free professional and room and inserts
    in one statement. If two requests race for the same slot, the constraint makes exactly one
    succeed, and the other gets a clear "slot taken" result.
  - Rationale: this satisfies R-05's "transaction with a lock" more strongly than an explicit row
    lock, and it is easy to prove.
  - The NFR-07 test runs **10 concurrent bookings of the same slot** on the **Neon test branch**
    and checks exactly 1 success and 9 "taken".
  - Alternative: pre-generated slot rows with `SELECT … FOR UPDATE`. It is closer to the PRD's
    wording, but it needs a job to create the slots.

- **Q8: What patient data the agenda stores, and how it fits pseudonymization and consent.**
  - Proposal for this spec: **no direct identifier**. An appointment stores:
    - a `subject`: an HMAC of the Telegram user id under the **same key** as SPEC-006, with a
      different prefix (`'agenda:' || from_id`), so the two subjects cannot be matched to each
      other;
    - the type, start and end, professional, room, status (`booked`, `cancelled`), the channel
      (`telegram`) and the creation time.
  - No name, phone, chat id or free text. The subject is enough for US-005 ("my appointment") in
    the later spec.
  - **Consequences to decide now or later:**
    - **(a) Reception cannot tell who is coming.** The PoC uses only test accounts. A real
      clinic needs at least a name or phone, which is direct personal data. Whether the booking
      spec asks for it, and on what legal basis, is a DEP-04 question.
    - **(b) Reminders need a way to reach the patient.** Telegram can only send to a chat id,
      and an HMAC cannot be reversed. The reminders spec will need the chat id stored, which is
      personal data, or another mechanism. It is not stored here.
    - **(c) The appointment type is health-related.** "Limpieza on day X" reveals that the person
      is a patient, which is special-category data under the GDPR, even pseudonymized. That is
      accepted for the demo with test accounts only; it is a DEP-04 question.

- **Q9: Consent and retention.**
  - Proposal:
    - booking (in the later spec) **requires consent in force** (SPEC-006). This spec only stores
      appointments;
    - consent for reminders is left to the reminders spec (CONF-005);
    - **retention**: an appointment is deleted **30 days after its end time**, by the agenda
      functions themselves, as the SPEC-006 consent purge does. 30 days matches NFR-08, and the
      clinic may need longer for its own records (DEP-04);
    - **withdrawing consent** does not cancel future appointments in this spec. What happens to
      them is left to the moving and cancelling spec.

- **Q10: Where the logic lives, and how it is tested.**
  - Proposal: everything in Neon: tables, constraints and SQL functions in
    `app/infra/sql/003_agenda.sql`, applied by `app/infra/schema.py`.
  - It is tested test-first with pytest against **the Neon test branch only**, as SPEC-006 K2
    was. That includes the NFR-07 concurrency test and the HOR-001 consistency test.
  - Applied to `main` only after the human confirms, with the same before-and-after read-only
    check as SPEC-006 K3.
  - No n8n change in this spec (RES-03: the agenda does not depend on the channel).

- **Q11: Initial data in main.**
  - Proposal: `main` gets only the configuration: opening hours, professionals, rooms and types,
    all marked as example. It gets **no appointments**.
  - Synthetic appointments, to fill slots, exist only inside the tests on the test branch, and
    each test removes them.

- **Q12: Who can see and change the agenda.**
  - Proposal: in this spec, only the SQL functions, used by the tests and later by n8n.
  - Reception's panel (RF-007) is out of scope. For the demo, reception's view is a read-only
    query documented in the README.

- **Q13: The clinic's real data.**
  - Proposal: every configuration value (hours, professionals, durations, booking window) is
    marked as example, like the urgency phone (SPEC-003) and the knowledge base (DEP-01).
  - The README says where to change each one.
  - Opening to real patients stays blocked, for the same reasons as now plus DEP-03.

## Assumptions

- **A1:** one clinic, one time zone (Europe/Madrid), Spanish only (PRD §7).
- **A2:** the agenda starts empty. It is not synchronized with LifeCenter's software (RES-01;
  charter §3, §8).
- **A3:** no real patients. Every test uses fake ids `900001…`, as in SPEC-006.
- **A4:** the SPEC-006 key in `consent_key` is reused only through a distinct HMAC prefix. It is
  never regenerated, and no second key table is created.

## Dependencies and conditions

- **DEP-03:** treatment durations and professional schedules. Every value in Q3–Q5 is
  provisional until then.
- **DEP-01:** the real opening hours (HOR-001) and holidays.
- **CONF-001:** what the bot may book. It is **resolved with option (a)** by the human for this
  project (Q4, 2026-11-22). The PRD's conflict log still shows it as open with Prince Calderon
  as decider, and it is not updated here.
- **DEP-04:** which patient data an appointment may hold, its retention, and consent for
  reminders (Q8, Q9).
- **AGENTS.md preflight:** the first task checks each Neon credential's host.
