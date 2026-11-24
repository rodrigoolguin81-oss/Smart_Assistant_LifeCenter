---
type: spec
spec_id: SPEC-009
title: reminders — Functional Spec
description: Requirements for a Telegram reminder the day before each appointment (US-006, RF-006, CONF-005) — a separate opt-in after booking, the chat id encrypted in its own table and deleted as soon as it is not needed, a generic text with no health data, the «Iré», «Cambiar» and «Anular» buttons, a scheduled workflow C that sends each reminder exactly once, outside quiet hours and never with less than 2 hours left, and the effect of moves, cancellations, consent withdrawal and a blocked bot. No B, no Gemini. EARS notation.
tags: [spec, reminders, SPEC-009, US-006, RF-006, CONF-005, SPEC-004, SPEC-006, SPEC-007, SPEC-008]
status: implemented
sources: [./clarifications.md, ../../docs/03-prd.md, ../007-agenda/spec.md, ../008-booking/spec.md, ../009-move-cancel/spec.md, ../006-consent/spec.md, ../005-pseudonymized-log/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# reminders — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-006), §5.1 (RF-006), §2 (no-shows), §7.8 (only
reminders as proactive messages), §8 (R-06), §10 (CONF-005), §9 (DEP-01, DEP-03, DEP-04). It
builds on SPEC-004 (`specs/007-agenda/`, Q8), SPEC-006 (`specs/006-consent/`), SPEC-007
(`specs/008-booking/`), SPEC-008 (`specs/009-move-cancel/`) and SPEC-005
(`specs/005-pseudonymized-log/`). Decisions in [clarifications](./clarifications.md).

## Context

Hoy el bot da, cambia y anula citas, pero no avisa antes. Esta spec añade un recordatorio por
Telegram el día antes de la cita:

- al reservar, el bot pregunta si el paciente quiere el recordatorio. Solo si dice que sí se
  guarda su chat de Telegram, cifrado y aparte;
- el recordatorio no dice qué tipo de cita es, porque se ve en la pantalla de bloqueo;
- trae los botones «Iré», «Cambiar», «Anular» y «Hablar con recepción»;
- lo envía un flujo nuevo programado (C), una sola vez, nunca de noche ni con menos de 2 horas
  de margen;
- si la cita se mueve, el recordatorio la sigue; si se anula, o el paciente retira el
  consentimiento, se borra.

B y Gemini no intervienen. El panel de recepción y otros canales vienen después.

**Definitions.**

- *Reminder*: the message C sends before an appointment, once.
- *Opt-in*: the patient's explicit «Sí, recuérdamela» for one appointment (clarifications Q2).
  It is separate from the SPEC-006 conversation consent, and needs it.
- *Reminder row*: a row of the new table `agenda_reminders`, one per appointment at most. It
  holds the appointment id, the chat id encrypted, the due time, the status, the attempts and
  the times. It holds no subject, name, type or text (clarifications Q3).
- *Chat id*: Telegram's `chat.id`. In a private chat it equals the user's `from.id`, so it is a
  direct identifier.
- *Reminder key*: the key that encrypts the chat id, in its own table `reminder_key`, generated
  inside Neon and never printed (clarifications Q3).
- *Due time*: the appointment's start minus `reminder_lead` (24 hours, example value).
- *Quiet hours*: 21:00–9:00 Madrid (example values). No reminder is sent in them.
- *Send window*: a reminder can be sent when it is due, outside quiet hours, and while the
  appointment starts more than `change_min_lead` (2 hours, SPEC-008) later.
- *Opt-in window*: the opt-in is offered only for an appointment that starts at least 3 hours
  later (clarifications Q7).
- *Workflow C*: the new n8n workflow `lifecenter-reminders`, run by a Schedule Trigger every 15
  minutes.
- *Reminder callbacks*, in the `bk:` namespace (SPEC-007), each at most 64 bytes. `<start>` is
  the appointment's start code, as in SPEC-008:

  | `callback_data` | Meaning |
  |---|---|
  | `bk:ry:<start>` | «Sí, recuérdamela» / «Recordármela el día antes» |
  | `bk:rn:<start>` | «No, gracias» |
  | `bk:rq:<start>` | «No quiero recordatorio» |
  | `bk:i:<start>` | «Iré» |

**Fixed texts.** Proposed by the agent from clarifications Q5 and Q13, and approved by the human at
the spec review (2026-11-23), who will check them in the Telegram test. Dates are Madrid dates,
as in SPEC-007.

- `REMINDER_OFFER_TEXT`: «¿Quieres que te recuerde la cita el día antes por aquí?» It is added
  to `BOOKED_TEXT` in the same message, with «Sí, recuérdamela» · «No, gracias» above
  «Cambiar» · «Anular» · «Hablar con recepción» (5 rows).
- `REMINDER_SET_TEXT`: «De acuerdo, te la recordaré el día antes.», followed by the «Mi cita»
  view.
- `REMINDER_OFF_TEXT`: «De acuerdo, no te enviaré recordatorio.», followed by the «Mi cita» view.
  It answers both «No, gracias» and «No quiero recordatorio».
- **The «Mi cita» view** (SPEC-008) gains one line and one button, while the appointment is in
  the opt-in window:
  - with a reminder: «Te recordaré la cita el día antes.» and «No quiero recordatorio»;
  - without one: «Recordármela el día antes».
- `REMINDER_TEXT`: «Recordatorio de LifeCenter: tienes una cita {cuándo}, a las {hora}, en
  {dirección}. Si no puedes venir, puedes cambiarla o anularla aquí.»
  - `{cuándo}` is «mañana, martes 1 de diciembre», or «hoy, martes 1 de diciembre» for a late
    reminder, or the full date when it is further away.
  - `{dirección}` is an example value, `CLINIC_ADDRESS`, until LifeCenter provides it (DEP-01).
  - It shows **no appointment type** (clarifications Q5).
  - Buttons: «Iré» · «Cambiar» · «Anular» · «Hablar con recepción».
- `ATTENDANCE_TEXT`: «Gracias, te esperamos.»
- `REMINDER_WITHDRAWN_LINE`: «No te enviaré recordatorios.», added to the SPEC-008 withdrawal
  text when the appointment had a reminder.
- A reminder button on an appointment that is no longer current gets SPEC-008
  `NOT_ACTIVE_TEXT` and the view.

## Requirements (EARS)

### Opt-in (CONF-005; clarifications Q2)

- RM1. WHEN an appointment is booked (`BOOKED_TEXT`) AND it starts at least 3 hours later, A
  SHALL add `REMINDER_OFFER_TEXT` and its two buttons to the same message. A SHALL NOT offer it
  after a move.
- RM2. WHEN «Sí, recuérdamela» or «Recordármela el día antes» is tapped, A SHALL call
  `reminder_set(from_id, start, chat_id)` once, and SHALL reply with `REMINDER_SET_TEXT`. IF the
  appointment is not current, THEN A SHALL reply with `NOT_ACTIVE_TEXT`. IF it starts in less
  than 3 hours, THEN A SHALL reply with the view, with no reminder button.
- RM3. WHEN «No, gracias» is tapped, A SHALL store nothing and SHALL reply with
  `REMINDER_OFF_TEXT`.
- RM4. WHEN «No quiero recordatorio» is tapped, A SHALL call `reminder_clear(from_id, start)`,
  which deletes the row and its chat id, and SHALL reply with `REMINDER_OFF_TEXT`.
- RM5. The «Mi cita» view SHALL show whether the current appointment has a reminder, and SHALL
  offer to add or remove it while the appointment is in the opt-in window.
- RM6. Every reminder step SHALL require consent in force (SPEC-006). Without it, the reminder
  callbacks SHALL get the SPEC-006 notice. «Iré» SHALL also require it: a reminder is only ever
  sent with consent in force (RM9).

### Storage and deletion (clarifications Q3, Q4)

- RM7. The chat id SHALL be stored only in `agenda_reminders`, encrypted with
  `pgp_sym_encrypt` under the reminder key. It SHALL be encrypted and decrypted inside Postgres,
  and SHALL never be stored in the agenda, the consent table or B.
- RM8. The reminder key SHALL be generated inside Neon by the schema step if it does not exist.
  It SHALL never be selected, printed or regenerated by any step. Its being in the same database
  is a known limitation (decision Q3).
- RM9. The chat id SHALL exist only while a reminder is pending. It SHALL be set to `NULL`:
  - when the reminder is sent (`sent`);
  - when it can no longer be sent (`skipped`, `failed`, `blocked`).

  The row SHALL be deleted:
  - when the appointment is cancelled;
  - when the patient taps «No quiero recordatorio»;
  - when the patient withdraws the general consent;
  - with the appointment, by the existing 30-day purge (cascade).
- RM10. WHEN an appointment with a reminder is moved (`agenda_move`), the reminder SHALL follow
  the new appointment, with its new due time and status `pending`. IF the new appointment is
  outside the send window when it becomes due, THEN RM15 applies.
- RM11. RM9 and RM10 SHALL be done by a trigger on `agenda_appointments` in the new SQL file. The
  SPEC-008 functions `agenda_cancel` and `agenda_move` SHALL NOT change.
- RM12. WHEN the patient withdraws the general consent, A SHALL delete the reminder of the
  current appointment in the same step, and SHALL add `REMINDER_WITHDRAWN_LINE` when there was
  one. The appointment SHALL stay (SPEC-008 MC11). IF that deletion fails, THEN the withdrawal
  SHALL still stand, and the reminder SHALL not be sent, because the claim checks consent (RM16).

### Sending (clarifications Q7–Q9)

- RM13. Workflow C SHALL run every 15 minutes. Each run SHALL claim the due reminders with
  `reminder_claim_due(limit)`, compose each message, send it, and record the result with
  `reminder_mark(id, result)`.
- RM14. A reminder SHALL be due at its due time. IF the appointment was booked less than
  `reminder_lead` ahead, THEN it SHALL be due at once.
- RM15. A reminder SHALL be sent only inside the send window. IF it is due during quiet hours,
  THEN it SHALL wait for the end of quiet hours. IF the send window has closed (less than 2
  hours left, or the appointment is past or no longer booked), THEN the claim SHALL mark it
  `skipped` and wipe its chat id, and nothing SHALL be sent. This covers a missed run while n8n
  was off.
- RM16. The claim SHALL be **at most once**. In one statement it SHALL:
  - select the due `pending` rows whose appointment is `booked`, in the future, and whose
    patient has consent in force, with `FOR UPDATE SKIP LOCKED`. The agenda subject cannot be
    turned into the consent subject (both are HMACs). In a private chat the chat id equals the
    `from.id` (clarifications A1), so the claim decrypts it inside Postgres and computes
    `consent_subject` from it. No new column is needed;
  - set them to `sending`, and count the attempt;
  - return the reminder id, the decrypted chat id, and the appointment's start and end.

  Two runs at the same time SHALL never claim the same row. A row left in `sending` for more than
  1 hour SHALL become `failed`, with its chat id wiped, and SHALL never be sent again.
- RM17. `reminder_mark` SHALL record:
  - `sent`: `sent_at` set, chat id wiped;
  - `blocked`, for Telegram 403 or "chat not found": chat id wiped, no retry;
  - `retry`, **only for Telegram 429** (surely not delivered): back to `pending` while fewer than
    3 attempts were made and the send window is open, otherwise `failed` with the chat id wiped;
  - `failed`, for a 5xx, a network error or any other error: chat id wiped, **no retry**, because
    Telegram may have delivered the message (decision of 2026-11-24, consistent with Q8: better a
    missing reminder than a duplicate).

  C SHALL send through «Enviar recordatorio» with `continueRegularOutput`, so an error arrives as
  `{error}` on the normal output and «Clasificar error» decides `sent`, `blocked`, `retry` or
  `failed` (decision of 2026-11-24, so the 403 and 429 cases can be tried with pinned data).
- RM18. The reminder SHALL use `REMINDER_TEXT`, with no appointment type, and its four buttons.
  It SHALL be sent by a Telegram node of C with 4 fixed rows and one expression per button field
  (SPEC-007 R6).

### Buttons of the reminder (clarifications Q6)

- RM19. WHEN «Iré» is tapped, A SHALL call `reminder_confirm(from_id, start)`, which sets
  `attendance_confirmed_at` on the appointment (decision Q6), and SHALL reply with
  `ATTENDANCE_TEXT`. A second tap SHALL change nothing and give the same reply. IF the
  appointment is not current, THEN A SHALL reply with `NOT_ACTIVE_TEXT` and the view.
- RM20. «Cambiar» and «Anular» SHALL be the SPEC-008 steps (`bk:x:<start>`, `bk:a:<start>`),
  unchanged, with their minimum notice. «Hablar con recepción» SHALL be the SPEC-006 handoff.

### Where it runs, privacy and logging (clarifications Q10, Q15)

- RM21. Workflow C SHALL call neither B nor Gemini, and SHALL have no webhook. It SHALL talk only
  to Neon (`Neon main`) and Telegram (the bot's credential).
- RM22. Workflow C SHALL save no executions (none / none / false / false), like A. The SPEC-005
  transient window applies to it, and is a known limitation.
- RM23. No log or counter table SHALL be added. The reminder rows and `attendance_confirmed_at`
  are the only records. Once final, a reminder row holds no chat id.

### SQL (clarifications Q12)

- RM24. A new file, `app/infra/sql/006_reminders.sql`, SHALL add:
  - the tables `agenda_reminders` and `reminder_key`, and the key generation;
  - the column `attendance_confirmed_at` on `agenda_appointments`;
  - the settings `reminder_lead` (24 hours), `reminder_quiet_from` (21:00) and
    `reminder_quiet_to` (9:00) on `agenda_settings`, all marked as example;
  - `reminder_set_at(from_id, start, chat_id, now)` / `reminder_set(from_id, start, chat_id)`;
  - `reminder_clear(from_id, start)` and `reminder_state(from_id)`;
  - `reminder_claim_due_at(limit, now)` / `reminder_claim_due(limit)` and `reminder_mark(id,
    result)`;
  - `reminder_confirm_at(from_id, start, now)` / `reminder_confirm(from_id, start)`;
  - `reminder_forget(from_id)`, used by A's withdrawal step;
  - the trigger of RM11.
- RM25. The public functions SHALL take no time parameter. Every function SHALL compute the
  subject in Postgres. Only the claim SHALL return a chat id, and no function SHALL return a
  subject, professional or room.
- RM26. The file SHALL be idempotent, and SHALL change neither the data of `kb_fragments`,
  `consent` and `consent_key`, nor the existing agenda rows (whose new column stays empty).

### Code, tests and order of work (clarifications Q11, Q14)

- RM27. The reminder texts, `CLINIC_ADDRESS` and the composition of the reminder SHALL live in a
  new module `n8n/code/recordatorios.js`, carried by C's Code node with its wiring and checked by
  a sync test against C's export. The new callbacks, the opt-in and the view lines SHALL live in
  `citas.js`.
- RM28. Node tests, written before the code, SHALL cover:
  - every new callback and the 64-byte limit;
  - every new text, `CLINIC_ADDRESS` marked as example, and `{cuándo}` for tomorrow, today and
    later dates, across both DST changes;
  - the opt-in window, the view lines, and the decisions of RM1–RM6 and RM19, with and without
    consent;
  - that every keyboard of A has 1–6 rows, and the reminder 4.
- RM29. The SQL SHALL be tested first with pytest on the Neon **test branch only**, with fake ids
  `9009xx` and the `_at` versions. The tests SHALL include:
  - due, quiet hours, late, `skipped`;
  - **two claims at the same time** → each row claimed once;
  - a stale `sending` row → `failed`;
  - the trigger on cancel and on move;
  - the deletions of RM9 and RM12;
  - the chat id encrypted in the table and wiped when final;
  - the key never returned by any function.

  The SQL SHALL be applied to `main` only after the human confirms, with a read-only check before
  and after.
- RM30. A and C SHALL be tested with pinned data under the SPEC-005 A4 extension approved on
  2026-11-23 (fake ids `9009xx`, one run per scenario, saving disabled at the end, every pinned
  datum removed and checked, the executions deleted by the human).
- RM31. The Telegram test SHALL be done in daytime (outside quiet hours), with n8n running, on an
  appointment booked more than 3 hours ahead (decision Q11). The reminder is then due at once
  (RM14), so no setting in `main` changes.
- RM32. The first task SHALL check the host behind each credential used (AGENTS.md "Preflight
  check").
- RM33. A and C SHALL be exported from their published versions, without `shared` and `pinData`,
  with no secret or personal data. The README SHALL describe reminders, C, the settings and the
  limitations.

## Acceptance criteria

**Node, SQL and pinned runs:**

- [ ] The `recordatorios.js` and `citas.js` tests are green: callbacks ≤ 64 bytes, texts, the
  example address, `{cuándo}` across DST, and keyboards of 1–6 rows (the reminder, 4).
- [ ] On the test branch:
  - `reminder_set` stores the chat id **encrypted** (the column never contains it in clear text)
    for the subject's current appointment, and `reminder_clear` deletes the row;
  - a due reminder outside quiet hours is claimed once, with the chat id; one in quiet hours waits;
    a late one inside the send window is claimed; one with less than 2 hours left, a past one, or
    one whose appointment is cancelled is `skipped` with no chat id;
  - **two claims at the same time** return each row once;
  - a `sending` row older than 1 hour becomes `failed` with no chat id;
  - `reminder_mark` gives `sent`, `blocked`, `retry` → `pending`, `failed` after 3 attempts, and
    `failed` at once for a 5xx or network error, with the chat id wiped when final;
  - cancelling the appointment deletes its reminder; moving it moves the reminder, with a new due
    time; withdrawing (`reminder_forget`) deletes it; a subject without consent is never claimed;
  - `reminder_confirm` sets `attendance_confirmed_at`, and a second call changes nothing;
  - no function returns the key, a subject, a professional or a room; the public functions have
    no time parameter;
  - re-applying the schema changes neither `kb_fragments`, `consent`, the keys nor the agenda rows.
- [ ] Pinned runs of A: the opt-in after booking (and not under 3 hours, and not after a move),
  «Sí», «No», «No quiero recordatorio», the view lines, «Iré», an old reminder button, every step
  without consent, and the withdrawal with and without a reminder.
- [ ] Pinned runs of C: nothing due; one due → sent and marked `sent`; 403 → `blocked`; 429 →
  `retry`; 5xx and network error → `failed`; a Neon failure in the claim or the mark. The message
  has no type and 4 buttons.

**From Telegram, in daytime, with n8n running and a test account with consent:**

- [ ] Booking an appointment more than 3 hours ahead shows the opt-in. «Sí, recuérdamela» →
  `REMINDER_SET_TEXT`. Within 15 minutes C sends the reminder: no type, the date, the time, the
  example address and 4 buttons. `main` has the row `sent` with no chat id (read-only check, no
  subject or chat id printed).
- [ ] «Iré» → `ATTENDANCE_TEXT`, and the appointment has `attendance_confirmed_at`.
- [ ] «Cambiar» from the reminder moves the appointment (SPEC-008).
- [ ] On another appointment with a reminder, «Anular» from the view, or from the opt-in message,
  deletes the reminder, which is never sent.
- [ ] «No, gracias» stores nothing.
- [ ] No B execution exists for any reminder step. C saves no executions.
- [ ] A and C are exported with no secret or personal data, and no pinned data remains.

## Known limitations

- **The laptop:** reminders only go out while n8n runs. A missed one is sent late only inside the
  send window, otherwise it is skipped. A server is needed for real use (RES-05).
- **The chat id is a direct identifier**, encrypted with a key in the same database (decision
  Q3). In production the key would live outside it.
- **C's transient window** (SPEC-005): n8n's local database briefly holds the running execution,
  with the chat id.
- **The address, the lead and the quiet hours are example values** (DEP-01, DEP-03).
- **«Iré» tells nobody** until the reception panel (RF-007).
- **At most once:** a crash of C between the claim and the send loses that reminder.

## Out of scope

- The reception panel and its view of confirmations (RF-007).
- Other channels, several reminders per appointment, and reminders for appointments made by
  reception.
- Measuring the no-show rate (PRD §2).
- Hosting n8n on a server (RES-05).
- Any change to B, to the consent tables, or to the SPEC-004, SPEC-007 and SPEC-008 SQL
  functions.
