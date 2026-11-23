---
type: clarifications
spec_id: SPEC-008
title: move and cancel — Clarifications
description: Open questions, each with the agent's proposal, before writing SPEC-008 (moving and cancelling one's own appointment from Telegram, US-005, RF-005) — ways in, confirmation, minimum notice, moving without losing the appointment, what is kept after cancelling, old buttons, future appointments when consent is withdrawn (SPEC-004 Q9), new SQL functions and texts.
tags: [clarify, move, cancel, SPEC-008, US-005, RF-005, NFR-07, SPEC-004, SPEC-006, SPEC-007]
status: verified
sources: [../../docs/03-prd.md, ../../docs/01-charter.md, ../007-agenda/clarifications.md, ../007-agenda/spec.md, ../008-booking/clarifications.md, ../008-booking/spec.md, ../006-consent/spec.md, ../005-pseudonymized-log/spec.md, ../004-urgencies/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# move and cancel — Clarifications

The human answered every question on 2026-11-23 (see **Decisions**). The questions are kept
below as they were asked, each with the agent's proposal. **Where a decision differs from a
proposal, the decision prevails.**

**Id and folder (Q1):** **SPEC-008** in `specs/009-move-cancel/`. `specs/index.md` and SPEC-004
Q1 list moving and cancelling as the second follow-up of SPEC-004 ("proposed SPEC-008"), and the
next free folder number is 009.

## What the PRD, the charter and the earlier specs say

**What this spec is for:**

- **US-005** (move or cancel): "Given un paciente con una cita futura asociada a su cuenta de
  Telegram / When el paciente pide cancelarla / Then Smart Assistant muestra la cita y pide
  confirmación / And al confirmar, libera el hueco en la agenda".
- **RF-005:** create, **move or cancel** appointments, **asking for explicit confirmation before
  writing to the agenda**.
- **Charter §4:** "Solicitud, cambio y cancelación de citas sobre una agenda propia del
  proyecto".
- **PRD §1 and §2:** 35 % of contacts are requests to book, move or cancel. 10 % of appointments
  are no-shows, and the target is 20 % fewer no-shows. Freeing a slot the patient will not use
  serves that goal.
- **CONF-004 (open):** the proposal (a) is to cut the depth of each Must. Option (b) would lower
  US-005 to Should. This spec keeps the depth small (Q3, Q14).
- **US-006 / RF-006 (reminders, later):** the reminder will have «confirmar asistencia» and
  «cancelar» buttons, so it will reuse this spec's cancel step.

**What the earlier specs give or require:**

- **SPEC-004 (the agenda, `003_agenda.sql`):**
  - an appointment has a `status` of `booked` or `cancelled`. **No function changes it yet**, and
    there is no `cancelled_at` column;
  - the exclusion constraints (per professional and per room) only apply to `booked` rows. A
    cancelled appointment frees its slot at once, and `agenda_free_slots` offers it again;
  - `agenda_book` checks the **limit of 1 future `booked` appointment per subject**, under an
    advisory lock per subject. So `agenda_book` cannot be used to move: the old appointment
    would trigger `limit`;
  - rows are deleted 30 days after their **end**, whatever their status (G17);
  - the settings are example values: 15-minute grid, `min_lead` 2 h, `horizon` 30 days, 1 future
    appointment;
  - **Q9:** "withdrawing consent does not cancel future appointments in this spec. **What happens
    to them is left to the moving and cancelling spec.**"
- **SPEC-007 (booking, `citas.js`, flow A):**
  - `/cita`, `/micita`, the `bk:` buttons (each ≤ 64 bytes, carrying its whole state), the slot
    code (minutes since the epoch, base 36), and `agenda_my_next(from_id)`;
  - the texts `BOOKED_TEXT`, `LIMIT_TEXT` and `MY_APPOINTMENT_TEXT` end with «Para cambiarla o
    anularla, (de momento) llama a recepción.»;
  - **the booking phrase negatives** (`evals/booking_phrases.yaml`) include «cancelar mi cita»,
    «cambiar mi cita», «quiero cancelar la cita», «necesito mover mi cita al jueves», «¿puedo
    anular la cita?» and «me cambiaron la cita». Today they go to B;
  - an urgency always wins over a booking phrase (BK2);
  - **R6 finding:** a booking keyboard has at most 5 rows, one per «Responder reserva (n)» node.
    A 6-row keyboard needs a sixth node and a sixth rule.
- **SPEC-006 (consent):**
  - every step needs consent in force. Withdrawal sets `revoked` and replies with
    `REVOKED_TEXT`. After it, every message gets the notice again;
  - a `revoked` record is deleted after 30 days.
- **SPEC-005:** A saves no executions. B receives only `question` and keeps its executions 30
  days.

## Coverage

**Proposed for this spec (SPEC-008):**

- seeing one's appointment with «Cambiar» and «Anular» buttons, under `/micita` and under the
  messages that show an existing appointment;
- free-text change and cancel phrases, which open that same view and never act on their own;
- **cancelling**, with a confirmation, which sets the appointment to `cancelled` and frees the
  slot;
- **moving** to another slot of the same type, with a confirmation, done as one transaction that
  keeps the old appointment if the new slot fails;
- a minimum notice, below which the patient is sent to reception;
- a safe answer to old buttons (an appointment that is past, cancelled or already moved);
- what happens to future appointments when consent is withdrawn (SPEC-004 Q9);
- new SQL functions in a new file, test-first on the test branch;
- the text changes in `citas.js`, and the new phrases in the dataset.

**Left for later specs:**

- **Reminders** (US-006, RF-006, CONF-005; proposed SPEC-009): the 24-hour message, its
  «confirmar asistencia» and «cancelar» buttons, and the chat id table. The cancel step of this
  spec is designed to be reused there.
- **The reception panel** (RF-007): seeing cancellations and moves, and identifying patients.
  For the demo, reception's read-only SQL view (README) shows the freed slots.
- Changing the **type** of an appointment (that is a cancel plus a new booking), choosing a
  professional, choosing dates by text («el jueves por la tarde»), and more than one future
  appointment per patient.
- Moving or cancelling an appointment **made by reception** or by phone: the agenda only has
  appointments made by the bot (`channel = 'telegram'`).

## Decisions (human, 2026-11-23)

- **Q2, Q3, Q5, Q6, Q7, Q9, Q10, Q11, Q12 and Q14:** the proposals are accepted as written.
- **Q1:** SPEC-008 in `specs/009-move-cancel/`, as proposed.
- **Q4: `change_min_lead` = 2 hours**, a configurable setting **marked as example data**. The
  clinic's real cancellation policy (for example 24 hours) is confirmed by LifeCenter under
  **DEP-03**.
- **Q8: option (a).**
  - Withdrawing consent **keeps** the future appointment.
  - The withdrawal message mentions it, with an «Anular mi cita» button.
  - **Cancelling and its confirmation are the only steps allowed without consent.**
  - The legal basis of the appointment after the withdrawal is pending **DEP-04**.
- **Q13: the SPEC-005 A4 exception is extended to this spec**, with the same conditions as in
  SPEC-006 and SPEC-007:
  - fake ids;
  - one run per scenario;
  - `saveManualExecutions` disabled at the end;
  - **all pinned data removed and checked**;
  - the human deletes the executions.

  It is recorded in the SPEC-005 clarifications too.
- **A1–A4:** accepted as written.

### Added at spec review (human, 2026-11-23)

- **Q8, extended.** «Mantener mi cita» also works **without consent**, but only as the way out
  of the cancel confirmation. It shows «De acuerdo, mantengo tu cita.» and nothing else. This is
  why that button carries the appointment's start (`bk:v:<start>`), unlike the «Mantener mi
  cita» of the move steps (`bk:v`), which needs consent.
- **Without consent, the allowed steps show only that appointment.** The cancelled text has no
  «Si quieres otra, escribe /cita.» and no «Pedir cita». «Esa cita ya no está activa.» and «De
  acuerdo, mantengo tu cita.» come without the «Mi cita» view. The agent's proposal is approved.
- **If the appointment lookup fails at withdrawal,** the withdrawal still goes ahead. The reply
  is `REVOKED_TEXT` followed by «Si tenías una cita reservada, se mantiene; para anularla, llama a
  recepción.», with an acceptance criterion.

## Questions, with the agent's proposals

- **Q1: Id and folder.**
  - Proposal: SPEC-008 in `specs/009-move-cancel/`, as above.
  - PRD §11's RF-005 row stays "SPEC-004", with SPEC-007 (booking) and SPEC-008 as its
    follow-ups. The index gets the new entry.

- **Q2: How does the patient ask?**
  - Proposal: **one view, «Mi cita», reached in three ways.** The view shows the appointment and
    the buttons «Cambiar» · «Anular» · «Hablar con recepción».
    1. **Buttons under the messages that already show the appointment:**
       - `/micita` (`MY_APPOINTMENT_TEXT`);
       - «Ya tienes…» (`LIMIT_TEXT`), after `/cita`, a booking phrase or a second «Confirmar»;
       - «Hecho: tienes…» (`BOOKED_TEXT`), right after booking.
    2. **Commands:** **no new command.** `/micita` is the way in, which keeps the command list
       short for the older patient persona.
       - Alternative: `/anular` and `/cambiar` as shortcuts to the same view. They add parsing,
         tests and texts for little gain.
    3. **Free text:** a fixed, strict list of change and cancel phrases, built like the booking
       phrases (SPEC-007 Q2):
       - positives such as «cancelar mi cita», «quiero anular la cita», «cambiar mi cita»,
         «necesito mover mi cita al jueves», «no puedo ir a mi cita»;
       - **a phrase never cancels or moves by itself.** It only opens the «Mi cita» view, so the
         detector does not need to tell cancelling from moving. «necesito mover mi cita al jueves»
         opens the view; the day is not parsed (as in SPEC-007 Q14);
       - **negatives** that keep going to B: «me cambiaron la cita» (it says what happened, and
         reception did it), «¿se puede cancelar sin coste?» and «¿cuánto cuesta cancelar?» (policy
         and price questions), «la cita de mi madre», «¿a qué hora es mi cita?». The last one
         could arguably open the view; the proposal keeps it a negative and lets `/micita` answer
         it, to stay strict;
       - these phrases **stay negatives of the booking detector**, and the SPEC-007 dataset is
         unchanged.
  - **Order in A for a text message**, extending SPEC-007 BK2:
    1. the urgency check, which **always wins** («quiero anular la cita, me sangra mucho la
       encía» gets the urgency reply);
    2. consent;
    3. **a change or cancel phrase** → the «Mi cita» view;
    4. a booking phrase → the booking flow;
    5. B.

    Change and cancel go before booking because they are the more specific intent: «quiero
    cambiar la cita que pedí» must not open the booking menu. A Node test checks the order with
    mixed messages.
  - **If the patient has no appointment**, the view shows `NO_APPOINTMENT_TEXT` with «Pedir cita»,
    as `/micita` does today.

- **Q3: Confirmation before cancelling or moving.**
  - Proposal: **always required** (RF-005, US-005). No button cancels or moves on the first tap.
    - **Cancel:** «Anular» → «¿Seguro que quieres anular {tipo} del {fecha} a las {hora}?»,
      with «Sí, anular» · «Mantener mi cita». Only «Sí, anular» writes.
    - **Move:** «Cambiar» → the slots for the same type (Q5) → a slot → «Vas a cambiar {tipo} del
      {fecha antigua} a las {hora antigua} al {fecha nueva} a las {hora nueva}. ¿Lo confirmo?»,
      with «Confirmar cambio» · «Elegir otro hueco» · «Mantener mi cita». Only «Confirmar
      cambio» writes.
  - «Mantener mi cita» writes nothing and shows the «Mi cita» view again.
  - The confirmation text always repeats the type, the date and the time (US-005: "muestra la
    cita").

- **Q4: Minimum notice: until when can the bot cancel or move?**
  - Facts: booking already needs 2 hours (`min_lead`). The PRD gives no cancellation policy, and
    the clinic has not stated one (DEP-03).
  - Proposal: **a new setting, `change_min_lead`, example value 2 hours**, the same as booking.
    It is checked against the start of the **current** appointment, for both cancelling and
    moving. Below it: «Tu cita es en menos de 2 horas. Para cambiarla o anularla, llama a
    recepción.», with «Hablar con recepción».
    - Rationale: reception is closed out of hours (PRD §1). A late cancellation through the bot
      still frees the slot and tells the clinic, while with a 24-hour rule the same patient
      would probably just not show up, which is what the PRD wants to reduce. The clinic can
      raise the value without a code change.
    - **Alternative: 24 hours** (a common clinic policy, and the reminder's moment, US-006).
      Below it the bot would send the patient to reception, at the cost of more calls and more
      no-shows out of hours.
    - Either way it is an example value until LifeCenter decides (DEP-03, DEP-04).
  - The **new** slot of a move follows the booking rules as they are (2 hours to 30 days ahead,
    grid, opening hours), checked by the same `agenda_slot_problem`.

- **Q5: Moving without losing the appointment.**
  - Proposal: **one SQL function does the whole move in one transaction**, under the subject's
    advisory lock (the same lock `agenda_book` uses):
    1. find the subject's `booked` appointment that starts at the old start, in the future. If
       there is none → `not_found` (Q7);
    2. check `change_min_lead` on the old start → `too_late`;
    3. check the new start with `agenda_slot_problem` for the **same type** → `invalid` with the
       reason; the new start equal to the old one → `invalid` (`same_slot`);
    4. set the old appointment to `cancelled`;
    5. insert the new one, trying each professional and room as `agenda_book` does;
    6. **if no pair is free, undo step 4** (the whole block runs in a subtransaction that is
       rolled back) and return `taken`. **The old appointment stays `booked`, unchanged.**
  - **How it fits the limit of 1:** the move function does not call `agenda_book`, so the limit
    check does not see the old appointment. Inside the lock, the subject goes from one future
    appointment to one future appointment. A `/cita` running at the same time for the same
    subject waits for the lock, and then gets `limit` because of the new appointment.
  - **How it fits the exclusion constraints:** they only apply to `booked` rows. Because the old
    row is cancelled **before** the insert, a move to an overlapping time with the same
    professional or room (for example 15 minutes later) is allowed. NFR-07 still holds: the
    insert is checked by the same constraints, and two patients racing for the new slot give one
    `moved` and one `taken`.
  - **What `taken` and `invalid` show:** «Ese hueco se acaba de ocupar. Tu cita del {fecha} a las
    {hora} sigue igual. Estos son los siguientes:», plus the next slots for the move.
  - The slots offered for a move **exclude the current appointment's start**.
  - Alternative, not proposed: book the new slot first, then cancel the old one. It would need
    to bypass the limit and would conflict with the constraints when the times overlap.

- **Q6: What is kept after cancelling, and what does the patient see?**
  - Proposal:
    - the row stays with **`status = 'cancelled'`**, and is deleted 30 days after its original
      **end**, by the existing purge (SPEC-004 G17). No new retention rule;
    - **two new operational columns**, added with `ADD COLUMN IF NOT EXISTS`:
      - `cancelled_at timestamptz`: when it was cancelled;
      - `replaced_by uuid`: on a moved appointment, the id of the new one.

      They contain no patient data. They let the old-button answer (Q7) and the PRD metrics
      tell a cancellation from a move.
      - Alternative: no new columns. A move and a cancellation then look the same in the agenda.
    - the patient sees: «Hecho: he anulado {tipo} del {fecha} a las {hora}. Si quieres otra,
      escribe /cita.», with «Pedir cita». Afterwards `/micita` shows `NO_APPOINTMENT_TEXT`, and
      `/cita` works again (the limit counts only `booked` rows);
    - the freed slot shows up in `agenda_free_slots` straight away.
  - Alternative: delete the row at once on cancel. That is less data, but it loses the
    cancellation count and the old-button answer, and reception could not see what happened.

- **Q7: Old buttons.**
  - Proposal: **every change and cancel button carries the start of the appointment it refers
    to.** The functions look for the subject's `booked` appointment **at that start**, so an old
    button can never act on a different appointment.
    - Example: the patient moves Monday 9:00 to Tuesday 10:00, and later taps an old «Anular» for
      Monday. Without the start in the button, it would cancel Tuesday.
  - Results for a button that no longer matches:
    - the appointment is **past**, or already **cancelled**, or was **moved** → `not_found`: «Esa
      cita ya no está activa.», followed by the current «Mi cita» view (the new appointment, or
      `NO_APPOINTMENT_TEXT` with «Pedir cita»);
    - with `replaced_by` (Q6) the text could say «Esa cita se cambió.» instead. Proposal: **one
      text for all**, which is enough and simpler.
  - A second tap on «Sí, anular» or «Confirmar cambio» gets `not_found`, followed by the current
    view, so a double tap is harmless (as in SPEC-007 Q6).
  - Consent is checked first, as for every step (SPEC-007 BK8), except as decided in Q8.

- **Q8: Future appointments when consent is withdrawn (SPEC-004 Q9).**
  - Facts: today a withdrawal leaves any future appointment `booked`, and the patient can no
    longer see or cancel it through the bot, because every booking step needs consent.
  - Options:
    - **(a) Keep the appointment and tell the patient.** The withdrawal is still immediate. If
      there is a future appointment, the `REVOKED_TEXT` gets one more line: «Tu cita de {tipo} el
      {fecha} a las {hora} sigue reservada. Si no vas a ir, puedes anularla aquí o llamar a
      recepción.», with an «Anular mi cita» button. **That button and its confirmation are the
      only steps allowed without consent,** because they only cancel. They show nothing beyond
      that appointment.
    - **(b) Cancel future appointments automatically** on withdrawal, and say so in the
      `REVOKED_TEXT`. Simple and minimal in data, but a patient who only wanted to stop the
      chat loses an appointment they meant to keep.
    - **(c) Ask before withdrawing:** «Retirar y anular mi cita» or «Retirar y mantener mi cita».
      It is the most explicit, but it adds a step and texts to the consent flow (SPEC-006).
    - **(d) Keep it, and say nothing.** That is today's behaviour, and the patient cannot reach
      the appointment through the bot.
  - **Proposal: (a).** The appointment is the service the patient asked for, and the clinic
    expects them. Withdrawing consent to the chat does not have to mean not going. The patient
    keeps a way to cancel without having to accept again.
    - The appointment's legal basis after withdrawal (service versus consent) is a **DEP-04**
      question for LifeCenter's management.
  - In every option, withdrawing does not delete the appointment row. It follows the normal
    30-day retention.

- **Q9: New SQL functions.**
  - Proposal: a new file **`app/infra/sql/005_move_cancel.sql`**, idempotent, following SPEC-004:
    public functions without a time parameter that call internal `_at` versions with `p_now` for
    the tests. All of them purge first and take the subject's advisory lock.

    | Function | Returns |
    |---|---|
    | `agenda_cancel_at(from_id, start, p_now)` / `agenda_cancel(from_id, start)` | `result` (`cancelled`, `not_found`, `too_late`), plus `type_code`, `starts_at`, `ends_at` of that appointment |
    | `agenda_move_at(from_id, old_start, new_start, p_now)` / `agenda_move(from_id, old_start, new_start)` | `result` (`moved`, `taken`, `invalid`, `not_found`, `too_late`), `reason` for `invalid`, `type_code`, the old and the new times. On `taken` or `invalid`, the old appointment is unchanged |

  - **Reading an appointment** for the confirmations (Q3) and the view: `agenda_my_next` already
    returns the next one. Because of the limit of 1, the «Mi cita» view needs nothing else. The
    confirmations check that the appointment at the button's start still exists before showing
    it, through `agenda_my_next` compared with the start, so no extra function is needed.
    - Alternative: `agenda_my_appointment_at(from_id, start, p_now)`, if the limit is ever
      raised.
  - **Next slots for a move**: the existing `agenda_free_slots(type, from, 3)`, with the current
    start filtered out in `citas.js`.
  - The functions return no professional, room, subject or id (as BK19).
  - **Tests first**, with pytest on the Neon **test branch only** (fake ids `9008xx`):
    - cancel: the row becomes `cancelled` and the slot is offered again; `not_found` for
      another subject's appointment, a past one, a cancelled one and a wrong start; `too_late`
      inside `change_min_lead`;
    - move: `moved` with the old row `cancelled` and `replaced_by` set; `taken`, `invalid` and
      `same_slot` leave the old row `booked` and unchanged; a move 15 minutes later with the same
      professional works;
    - **concurrency:** two patients moving into the same free slot give 1 `moved` and 1 `taken`,
      and the loser keeps their appointment. A move and a `/cita` of the same subject at the same
      time give 1 `moved` and 1 `limit`. A double «Sí, anular» gives 1 `cancelled` and 1
      `not_found`;
    - re-applying the schema leaves `kb_fragments`, `consent`, the key and the agenda rows
      unchanged.
  - Applied to `main` only after the human confirms, with the read-only check before and after
    (SPEC-004 G20).

- **Q10: Buttons and `callback_data`.**
  - Proposal: new letters in the `bk:` namespace, so `consentimiento.js` keeps routing them as
    `booking_button`. The `<start>` uses the SPEC-007 slot code. The type is not in the button:
    the functions read it from the appointment.

    | `callback_data` | Meaning |
    |---|---|
    | `bk:v` | the «Mi cita» view |
    | `bk:a:<start>` | «Anular» → the cancel confirmation |
    | `bk:ac:<start>` | «Sí, anular» |
    | `bk:x:<start>` | «Cambiar» → the slots for the move |
    | `bk:xm:<start>:<from>` | «Ver más» while moving |
    | `bk:xs:<start>:<new>` | a slot while moving → the move confirmation |
    | `bk:xc:<start>:<new>` | «Confirmar cambio» |

    The longest, `bk:xc:xxxxx:xxxxx`, is 17 bytes. A Node test checks every value against the 64
    bytes, as in SPEC-007.
  - **The R6 keyboard limit:** the move slot list would have 3 slots, «Ver más», «Mantener mi
    cita» and «Hablar con recepción», which is **6 rows**. Today A has nodes for 1–5.
    - Proposal: **add «Responder reserva (6)»** and a sixth rule, keeping the generic pattern,
      and extend the 1–5 test to 1–6.
    - Alternative: drop «Mantener mi cita» from the move slot list, since «Hablar con recepción»
      and doing nothing also keep the appointment. That keeps 5 rows, but it is less clear for
      the older patient.

- **Q11: Texts for each result.** Proposed, all fixed, with `{tipo}` with its article as in
  SPEC-007. The changed SPEC-007 texts drop «llama a recepción», because the buttons replace it.
  - **Changed (SPEC-007 texts):**
    - `BOOKED_TEXT`: «Hecho: tienes {tipo} el {fecha} a las {hora}.», with «Cambiar» · «Anular» ·
      «Hablar con recepción».
    - `LIMIT_TEXT`: «Ya tienes {tipo} el {fecha} a las {hora}. Solo se puede tener una cita
      reservada por el bot.», with the same buttons.
    - `MY_APPOINTMENT_TEXT`: «Tu próxima cita: {tipo} el {fecha} a las {hora}.», with the same
      buttons.
  - **New:**
    - `CANCEL_CONFIRM_TEXT`: «¿Seguro que quieres anular {tipo} del {fecha} a las {hora}?» · «Sí,
      anular» · «Mantener mi cita».
    - `CANCELLED_TEXT`: «Hecho: he anulado {tipo} del {fecha} a las {hora}. Si quieres otra,
      escribe /cita.» · «Pedir cita».
    - `MOVE_SLOTS_TEXT`: «¿A cuándo quieres cambiar {tipo} del {fecha} a las {hora}? Estos son los
      primeros huecos:» · the slots, «Ver más», «Mantener mi cita», «Hablar con recepción».
    - `MOVE_MORE_SLOTS_TEXT`: «Estos son los siguientes huecos:» · the same buttons.
    - `MOVE_CONFIRM_TEXT`: «Vas a cambiar {tipo} del {fecha} a las {hora} al {fecha nueva} a las
      {hora nueva}. ¿Lo confirmo?» · «Confirmar cambio» · «Elegir otro hueco» · «Mantener mi
      cita».
    - `MOVED_TEXT`: «Hecho: {tipo} pasa al {fecha nueva} a las {hora nueva}. La cita anterior
      queda anulada.» · «Cambiar» · «Anular» · «Hablar con recepción».
    - `MOVE_TAKEN_TEXT`: «Ese hueco se acaba de ocupar. Tu cita del {fecha} a las {hora} sigue
      igual. Estos son los siguientes:» · the slots.
    - `MOVE_UNAVAILABLE_TEXT`: «Ese hueco ya no está disponible. Tu cita del {fecha} a las {hora}
      sigue igual. Estos son los siguientes:» · the slots.
    - `MOVE_NO_SLOTS_TEXT`: «Ahora mismo no hay otros huecos para {tipo} en los próximos 30 días.
      Tu cita sigue igual. Llama a recepción para buscar otra fecha.» · «Hablar con recepción».
    - `TOO_LATE_TEXT`: «Tu cita es en menos de {plazo}. Para cambiarla o anularla, llama a
      recepción.» · «Hablar con recepción».
    - `NOT_ACTIVE_TEXT`: «Esa cita ya no está activa.», followed by the current «Mi cita» view.
    - `KEPT_TEXT`, after «Mantener mi cita»: «De acuerdo, mantengo tu cita.», followed by the
      «Mi cita» view.
    - With Q8 (a), `REVOKED_WITH_APPOINTMENT_TEXT`: the `REVOKED_TEXT` plus «Tu cita de {tipo} el
      {fecha} a las {hora} sigue reservada. Si no vas a ir, puedes anularla aquí o llamar a
      recepción.» · «Anular mi cita».
    - A Neon failure on any step → the D7 text with «Hablar con recepción», as in SPEC-007 BK20.
      A failure at «Sí, anular» or «Confirmar cambio» cannot tell whether it was saved, and
      `/micita` resolves it.

- **Q12: Where the logic lives, privacy and logging.**
  - Proposal: the same pattern as SPEC-007:
    - everything in **flow A and Neon**. B and Gemini are never called for a change or a cancel,
      and B still receives only `question`;
    - the texts, the codec, the phrase detector and the decisions go in **`citas.js`**, extended
      test-first, with the sync check against A's export. A separate module is the alternative,
      but the steps share the codec, the dates and the «Mi cita» view;
    - A keeps its SPEC-005 settings and saves no executions. No new log or counter table. The
      only record is the appointment row, with `cancelled_at` and `replaced_by` (Q6).

- **Q13: Order of work and tests.**
  - Proposal: the same order as SPEC-007:
    1. **preflight**, read-only: the credential hosts (AGENTS.md), SPEC-004 and SPEC-007
       functions on both branches, and the exports equal to the published versions;
    2. **`citas.js`** and its Node test first: the new callbacks and the 64-byte limit, the
       phrase dataset with positives and negatives, the urgency order, every text and decision,
       and the 1–6 keyboard rows (Q10);
    3. **`005_move_cancel.sql`** test-first on the test branch, then `main` after the human
       confirms;
    4. **A** through the MCP, tested with pinned data **under the SPEC-005 A4 extension**, which
       needs the human's approval again: fake ids `9008xx`, one run per scenario,
       `saveManualExecutions` disabled at the end, every pinned datum removed and checked, and the
       executions deleted by the human. **B does not change**;
    5. the human publishes A and tests from Telegram, using the appointment kept for the demo;
    6. exports and docs.

- **Q14: Scope limits.**
  - Proposal, to keep the depth small (CONF-004 a):
    - a move keeps the **same type**. Another type is a cancel plus `/cita`;
    - only **the patient's own bot appointments** can be changed (the subject), and only `booked`
      future ones;
    - no reason for cancelling is asked or stored;
    - no message to reception about a cancellation or a move until RF-007. The freed slot is
      visible in reception's read-only SQL view.

## Assumptions

- **A1:** private chats only, as in SPEC-006 A1 and SPEC-007 A1.
- **A2:** test accounts only, and the agenda's example data (SPEC-004).
- **A3:** the limit stays at 1 future appointment per subject, so «Mi cita» is always a single
  appointment. If the limit is raised later, the view needs a list.
- **A4:** the SPEC-004 and SPEC-007 functions are used as they are. Only the new functions,
  columns and setting of Q4, Q6 and Q9 are added.

## Known limitations (expected)

- **Reception is not told** about cancellations or moves until RF-007. It sees them only in the
  read-only SQL view.
- **The minimum notice is an example value** until the clinic states its policy (Q4).
- **A's transient window** (SPEC-005) applies to these messages too.
- **The free-text detector is a phrase list.** Unusual wordings go to B, and `/micita` always
  works.
- **A failure at «Sí, anular» or «Confirmar cambio»** cannot tell whether it was saved.
  `/micita` resolves it.

## Dependencies and conditions

- **SPEC-004** and **SPEC-007** implemented, with their functions in `main`. **SPEC-006** in force.
- **DEP-03 / DEP-04:** the minimum notice (Q4), and the legal basis of an appointment after the
  consent is withdrawn (Q8).
- **CONF-004:** open. This spec keeps the depth small (Q14).
- **AGENTS.md preflight:** the first task checks each Neon credential's host.
- **Opening to real patients stays blocked**, for the reasons already listed in SPEC-004 to
  SPEC-007.
