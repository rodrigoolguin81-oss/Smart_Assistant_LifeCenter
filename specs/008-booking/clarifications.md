---
type: clarifications
spec_id: SPEC-007
title: booking — Clarifications
description: Questions resolved with the human before writing SPEC-007 (booking an appointment from Telegram on the SPEC-004 agenda, US-004, RF-005 create, NFR-07) — what it covers, what it leaves for later (moving, cancelling, reminders, reception panel), and how it fits consent (SPEC-006), urgencies (SPEC-003) and offer_booking (SPEC-001).
tags: [clarify, booking, SPEC-007, US-004, RF-005, NFR-07, CONF-001, SPEC-004, SPEC-006]
status: verified
sources: [../../docs/03-prd.md, ../../docs/01-charter.md, ../007-agenda/spec.md, ../007-agenda/clarifications.md, ../006-consent/spec.md, ../002-answer-generation/spec.md, ../002-answer-generation/clarifications.md, ../004-urgencies/spec.md, ../005-pseudonymized-log/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# booking — Clarifications

The human answered on 2026-11-22 (see **Decisions**). The questions are kept below as they were
asked, each with the agent's proposal. **Where a decision differs from a proposal, the decision
prevails.**

**Id and folder (Q1):** **SPEC-007** in `specs/008-booking/`. This follows `specs/index.md`,
which lists booking from Telegram as the first follow-up of SPEC-004 ("proposed SPEC-007"), and
the folder numbering (007 is the agenda).

## What the PRD, the charter and the earlier specs say

**What this spec is for:**

- **US-004** (book a free slot):
  - "Given … existen huecos libres para 'revisión' … When el paciente pide cita para una
    revisión";
  - "Then Smart Assistant ofrece hasta 3 huecos con botones";
  - "tras elegir uno, repite fecha, hora y tratamiento";
  - "solo crea la cita cuando el paciente confirma".
- **RF-005:** look up availability and create appointments, **asking for explicit confirmation
  before writing to the agenda**. Moving and cancelling are left for later.
- **NFR-07 / R-05:** 0 double bookings with 10 simultaneous requests. **SPEC-004 already
  guarantees this in the database** (exclusion constraints; 10 concurrent bookings give 1
  `booked` and 9 `taken`). This spec must keep it true end to end.
- **CONF-001** (resolved with option a in SPEC-004 Q4): the bot books revisión, limpieza and
  primera visita. Blanqueamiento and long treatments can only be **requested**.
- **Targets (PRD §2, charter §5):** at least 20 % of appointments created by the bot by the end
  of the pilot.
- **PRD personas:** the older patient needs "mensajes cortos, botones claros y poder pedir en
  todo momento 'hablar con una persona'".

**What the earlier specs give or require:**

- **SPEC-001 R14 (`offer_booking`):** a validated answer that cites a fragment of `tipo`
  `tarifa` or `tratamiento` sets `offer_booking: true`, and never when abstaining. SPEC-001 Q14
  says: "n8n will show the button once SPEC-004 exists".
  - **Fact:** the n8n demo does not implement it. B's "Validar y componer" returns `text`,
    `handoff`, `reason` and `citations`, but no `offer_booking`. B's "Resultado" whitelist does
    not include it.
  - The cited fragments in "Validar y componer" do carry `tipo` (TAR-001 `tarifa`, TRA-001
    `tratamiento`, HOR-001 `horario`).
- **SPEC-004 (the agenda):**
  - `agenda_free_slots(type, from, limit = 3)` returns `free` slots, or `request_only`.
  - `agenda_book(type, start, from_id)` returns `booked`, `taken`, `limit`, or `invalid` with a
    reason.
  - Both use `now()`. The patient is stored only as an HMAC subject.
  - G14 left **confirmation and consent** to this spec.
  - **There is no function to read a patient's own appointment** (needed for `/micita` and for
    the `limit` message).
- **SPEC-006 (consent, flow A):**
  - A checks consent before any processing, and urgencies are always answered first.
  - Commands, buttons and their `callback_data` (≤ 64 bytes) are parsed in `consentimiento.js`.
  - A knows the `from.id` and saves no executions. B receives only `question`.
- **SPEC-003:** "tengo una cita el lunes" is a *non-urgency* example, so a booking-intent
  detector must not take every "cita" as a request either.
- **SPEC-005:** A stores nothing. B's executions are pseudonymized and kept 30 days.

## Coverage

**Proposed for this spec (SPEC-007):**

- the ways in: `/cita`, a «Pedir cita» button after an answer with `offer_booking`, and simple
  booking phrases in free text;
- choosing the type, including what happens with request-only types;
- showing up to 3 slots as buttons, with «Ver más»;
- **the confirmation step** (US-004, RF-005), then `agenda_book`;
- a message for every result (`booked`, `taken`, `invalid`, `limit`, error);
- `/micita`, to see one's next appointment;
- the minimal B change that makes `offer_booking` real (Q7);
- a read-only SQL function for "my next appointment" (Q10).

**Left for later specs:**

- **Moving and cancelling** (US-005, RF-005), **proposed SPEC-008**. It includes what happens
  to future appointments when consent is withdrawn (SPEC-004 Q9). Until then, the messages say
  "para cambiarla o anularla, llama a recepción".
- **Reminders** (US-006, RF-006, CONF-005), **proposed SPEC-009**, with the chat id in a
  separate table and its own consent.
- **The reception panel**, and how reception identifies who is coming (RF-007).
- Choosing a professional, choosing a date range by text ("la semana que viene", "el jueves por
  la tarde"), and booking for someone else.

## Decisions (human, 2026-11-22)

- **Q2: free text, yes, with a fixed and strict list of clear phrases.**
  - It is detected **after the urgency check and the consent check**.
  - It **only opens the type menu**, or goes straight to the slots when the text names a
    bookable type. It **never books without confirmation**.
  - The test must include **negative cases**, which are not a booking request and keep going to
    B as today:
    - «tengo una cita el lunes»;
    - «¿cuánto cuesta una cita?»;
    - «cancelar mi cita» (that is SPEC-008);
    - and similar ones (moving, asking about an existing appointment, prices).
- **Q3: accepted.** The request-only text and its alternative: book a first visit, or talk to
  reception.
- **Q7: `offer_booking` is computed in B**, from the `tipo` of the cited fragments (`tarifa` or
  `tratamiento`, SPEC-001 R14), with no Gemini.
  - "Resultado" adds it to its whitelist.
  - **B is published before A**, as in SPEC-005, because A reads the new field.
- **Q13: the SPEC-005 A4 exception is extended to this spec**, with the same conditions as in
  SPEC-006:
  - fake ids `9000xx`;
  - one run per scenario;
  - `saveManualExecutions` is disabled at the end;
  - **all pinned data removed and checked**;
  - the human deletes the executions.

  It is recorded in the SPEC-005 clarifications too.
- **Q1, Q4–Q6, Q8–Q12, Q14, Q15 and A1–A4:** the proposals are accepted.

## Questions as asked, with the agent's proposals

- **Q1: Id and folder.**
  - Proposal: SPEC-007 in `specs/008-booking/`, as above.
  - PRD §11's RF-005 row stays "SPEC-004", with SPEC-007 as its booking follow-up.

- **Q2: How does the patient ask for an appointment?**
  - Proposal: **three ways in, all leading to the same flow:**
    1. the **`/cita`** command, case-insensitive as in SPEC-006;
    2. a **«Pedir cita»** button under an answer that has `offer_booking: true` (SPEC-001 R14).
       The answer still shows the price and its notices, and «Hablar con recepción» stays where
       it applies;
    3. **free text with a clear booking intent**, detected deterministically in A, such as «quiero
       pedir cita», «¿puedo reservar una limpieza?» or «dame cita para una revisión».
       - A short phrase list ("pedir/reservar/coger/dar/quiero … cita", "reservar …") with a
         dataset and a Node test, as in SPEC-003.
       - "tengo una cita…" and other mentions of an existing appointment are **not** a request:
         they keep going to B as today.
       - When in doubt, it is **not** a booking: the message goes to B as now, so the cost of a
         miss is an ordinary answer.
  - Order in A for a text message:
    1. the urgency check (SPEC-003);
    2. consent (SPEC-006);
    3. then booking intent;
    4. then B.

    So «me duele una muela, quiero cita» gets the urgency reply, never the booking flow.

- **Q3: How is the type chosen, and what about request-only types?**
  - Proposal: a **type menu** with buttons: «Revisión» · «Limpieza» · «Primera visita» · «Otro
    tratamiento».
  - If the text or the button already names a bookable type («reservar una limpieza»), the menu
    is skipped and the bot goes straight to the slots.
  - «Otro tratamiento», or a request-only type named in the text (blanqueamiento, implantes,
    ortodoncia), gets: «Ese tratamiento necesita una valoración previa en la clínica. Puedo
    reservarte una primera visita, o puedes hablar con recepción.» It comes with the buttons
    «Primera visita» and «Hablar con recepción».
  - This is the CONF-001 (a) rule. A real "request" to reception needs RF-007, which does not
    exist, so the request is the handoff text.
  - The menu shows the types' names from the agenda, not their durations or prices.

- **Q4: How are the slots shown?**
  - Proposal: «Estos son los primeros huecos para {tipo}:» with **one button per slot** (up to 3,
    from `agenda_free_slots`), labelled in Madrid time «lun 7 dic · 9:00».
  - Below them, a **«Ver más»** button, which asks for the next 3 starting after the last one
    shown, and «Hablar con recepción».
  - The professional is not shown. US-004 asks for date, time and treatment, and the staff names
    are example data.
  - If there are no free slots in the 30-day window: «Ahora mismo no hay huecos libres para {tipo}
    en los próximos 30 días. Llama a recepción para buscar otra fecha.», with «Hablar con
    recepción».

- **Q5: How does a slot fit in 64 bytes of `callback_data`, and what if it is taken by the time
  the patient taps?**
  - Proposal: **the button carries the slot itself**, with no server-side state (A stores
    nothing):
    - type select: `bk:t:<type>`;
    - slot select: `bk:s:<type>:<start>`;
    - confirm: `bk:c:<type>:<start>`;
    - see more: `bk:m:<type>:<start>`;
    - other treatment: `bk:o`.
  - `<start>` is the start as **minutes since the Unix epoch, in base 36** (5 characters until
    2084). The longest value, `bk:c:tratamiento_largo:xxxxx`, is 28 bytes. A Node test checks
    every value against the 64-byte limit, as in SPEC-006.
  - A version suffix, as in SPEC-006, is not needed here: `agenda_book` re-checks everything when
    the patient confirms.
  - **The slot is never trusted from the button.** `agenda_book` re-checks every rule at
    confirmation time.
    - If it was taken in between → `taken`: «Ese hueco se acaba de ocupar. Estos son los
      siguientes:», plus the next 3 slots.
    - If it is no longer valid (an old message, now less than 2 hours ahead, or a changed
      configuration) → `invalid`: «Ese hueco ya no está disponible. Estos son los siguientes:»,
      plus the next 3.
  - Tapping a slot only shows the confirmation. It books nothing.

- **Q6: Is there a confirmation step before booking?**
  - Proposal: **yes, always**, as US-004 and RF-005 require.
  - After a slot is tapped: «Vas a reservar {tipo} el {lunes 7 de diciembre} a las {9:00}. ¿Lo
    confirmo?», with «Confirmar» and «Elegir otro hueco» (which shows the slots again from now).
  - Only «Confirmar» calls `agenda_book`.
  - A second tap on the same «Confirmar», or on an old one, gets `limit` (the patient already has
    that appointment). The limit message then shows the existing appointment, so a double tap is
    harmless.

- **Q7: Where does the logic live, and what about B and Gemini?**
  - Proposal: **in A and Neon only.** A knows the `from.id` and calls the public
    `agenda_free_slots` / `agenda_book` directly.
    - **B is never called for booking**, and B never receives `from.id`, the subject or the
      slot. SPEC-005 P5 still holds: B receives `question` only.
    - **No Gemini** in any booking step: the flow is buttons, fixed texts and SQL, and it is
      deterministic.
  - The booking logic goes in a module **`n8n/code/citas.js`**: callback encoding and parsing,
    the intent detector, date formatting and the texts. It has its own Node test and a sync check
    with A's export, as `consentimiento.js` does (SPEC-006 C23–C25).
  - **`offer_booking`, the only B change:** B's "Validar y componer" sets `offer_booking: true`
    when an answered reply cites a fragment of `tipo` `tarifa` or `tratamiento` (SPEC-001 R14).
    "Resultado" adds `offer_booking` to its whitelist. It is not an identifier, so P6 still
    holds.
  - Alternative: A guesses it from the citation prefixes (`TAR-`, `TRA-`) without touching B. It
    is simpler, but it depends on a naming convention.

- **Q8: Consent, the limit and the urgency order.**
  - Proposal:
    - **Consent in force is required for every booking step**: `/cita`, `/micita`, every `bk:`
      button, and a booking phrase. Without it, the bot replies with the SPEC-006 notice, and
      the request is discarded, as for any other message (SPEC-006 C4).
    - The SPEC-004 **limit of 1 future appointment** is enforced by `agenda_book` (`limit`).
      Additionally, `/cita` checks first: if the patient already has an appointment, they get
      the `limit` message straight away, without going through the menu and the slots for
      nothing.
    - Urgencies come first, as in Q2.
    - Booking messages always carry «Hablar con recepción» (PRD persona).

- **Q9: The message for each result.** Proposed texts, all fixed:
  - **booked:** «Hecho: tienes {tipo} el {lunes 7 de diciembre} a las {9:00}. Para cambiarla o
    anularla, de momento llama a recepción.»
  - **taken:** «Ese hueco se acaba de ocupar. Estos son los siguientes:», plus the slots.
  - **invalid:** «Ese hueco ya no está disponible. Estos son los siguientes:», plus the slots.
  - **limit:** «Ya tienes una cita: {tipo} el {fecha} a las {hora}. Para cambiarla o anularla,
    llama a recepción.»
  - **request_only:** the Q3 text.
  - **no slots:** the Q4 text.
  - **Neon error**, on any booking step: the D7 text «Ahora mismo no puedo responder. ¿Quieres
    que pase tu consulta a recepción?», with «Hablar con recepción». Nothing is booked.
  - Dates are always Madrid local time, in Spanish («lunes 7 de diciembre», «9:00»).

- **Q10: How does the patient see their appointment afterwards?**
  - Proposal: a **`/micita`** command.
    - «Tu próxima cita: {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, llama a
      recepción.»
    - or «No tienes ninguna cita reservada. Escribe /cita para pedir una.»
  - It needs a **new read-only SQL function** in `app/infra/sql/004_booking.sql`, for example
    `agenda_my_next(from_id)`. It returns only the type name and the start and end of the
    subject's next `booked` appointment, never the professional or the subject.
  - It is written test-first on the test branch, as in SPEC-004.
  - `/privacidad` and `/start` do not show the appointment.

- **Q11: What is logged, with no personal data?**
  - Proposal: **nothing new.**
    - A saves no executions (SPEC-005), so the booking dialogue leaves no n8n trace, except the
      known window of about 15 minutes in n8n's local database.
    - B is not involved.
    - The only record is the appointment row itself: subject, type and times (SPEC-004 G15).
  - The PRD target "citas creadas por el bot / citas totales" is computed from
    `agenda_appointments` with `channel = 'telegram'`. No extra table or counter is added.
  - Optional, not proposed: an anonymous daily counter per result (`booked`, `taken`, …) to
    measure friction. It would need its own table and retention.

- **Q12: What if Neon fails in the middle of the dialogue?**
  - Proposal: every Neon call in the flow has an error output. Its message is the D7 text with
    «Hablar con recepción», as SPEC-006 C6 does.
  - Because the state lives in the buttons, the patient can simply tap again or write `/cita`.
  - A failure at «Confirmar» does not tell whether the booking was saved, so the D7 text is
    shown. `/micita` lets the patient check afterwards.

- **Q13: Code, tests and the order of the work.**
  - Proposal: the same order as SPEC-003, SPEC-006 and SPEC-004:
    1. **Preflight**, read-only (AGENTS.md): the credential hosts, and that SPEC-004's
       functions exist on both branches.
    2. **`citas.js`** with its Node test, written first:
       - callback encoding and the 64-byte limit;
       - parsing;
       - the intent dataset, positives and negatives such as "tengo una cita el lunes";
       - date formatting across DST;
       - the texts.
    3. **`004_booking.sql`** (`agenda_my_next`), with pytest on the test branch, then `main` after
       the human confirms.
    4. **B's `offer_booking`** and **A's booking nodes**, tested with pinned data. This extends
       SPEC-005 A4 again, to be approved: synthetic ids, one run per scenario, then disabled,
       and the human deletes the executions.
    5. The human publishes and tests from Telegram.
    6. Exports and docs.
  - A concurrency check end to end: two Telegram accounts confirming the same slot at the same
    time. It is optional, because NFR-07 is already proven in the database (SPEC-004), and two
    people would have to tap at once.

- **Q14: Free-text details.**
  - Proposal:
    - the phrase detector runs on the **pseudonymized** text, after the urgency check;
    - it recognizes a bookable type named in the same sentence (revisión, limpieza, primera
      visita) to skip the menu, and the request-only words (blanqueamiento, implantes,
      ortodoncia) to go to the Q3 text;
    - no dates or times are parsed from text in this spec.

- **Q15: Language and format of dates and buttons.**
  - Proposal:
    - button labels at most about 20 characters («lun 7 dic · 9:00»), so they fit on a phone;
    - one slot per row;
    - the confirmation and the `booked` text spell the date out in full («lunes 7 de
      diciembre»);
    - no year, unless the date is in the next calendar year («lunes 4 de enero de 2027»).

## Assumptions

- **A1:** private chats only, as in SPEC-006 A1. The subject comes from `from.id`.
- **A2:** test accounts only. No real patients, and the agenda's example data (SPEC-004).
- **A3:** the SPEC-004 functions are used as they are. The public ones always use `now()`, and
  only the new `agenda_my_next` is added.
- **A4:** one appointment per booking. No series, and no booking for someone else.

## Known limitations

- **Reception cannot see who booked** (SPEC-004). That is the reception panel's job, RF-007.
- **No reminders and no self-service changes yet.** The texts send the patient to reception for
  any change.
- **A's transient window** (SPEC-005): during the booking dialogue, n8n's local database briefly
  holds the raw update, including the `from.id`, for up to about 15 minutes.
- **Free-text detection is a phrase list.** Unusual wordings fall through to B and get an
  ordinary answer. `/cita` and the «Pedir cita» button always work.

## Dependencies and conditions

- **SPEC-004** implemented (its functions in `main`). **SPEC-006** in force for consent.
- **DEP-01 / DEP-03:** the hours, types and durations are still example data.
- **DEP-04:** the appointment type is health data (SPEC-004). It is kept 30 days after the
  appointment.
- **Opening to real patients stays blocked**, for the reasons already listed in SPEC-004/005/006.
