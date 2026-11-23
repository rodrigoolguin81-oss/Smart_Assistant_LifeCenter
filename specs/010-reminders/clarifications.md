---
type: clarifications
spec_id: SPEC-009
title: reminders — Clarifications
description: Open questions, each with the agent's proposal, before writing SPEC-009 (a Telegram reminder 24 hours before each appointment, US-006, RF-006, CONF-005) — consent for proactive messages, how the chat id is stored and deleted, a reminder text that shows no health data on the lock screen, its buttons, when it is sent and what happens if n8n was off, sending exactly once, changed or cancelled appointments and blocked bots, a new scheduled flow C, testing without waiting 24 hours, and the new SQL functions.
tags: [clarify, reminders, SPEC-009, US-006, RF-006, CONF-005, SPEC-004, SPEC-006, SPEC-007, SPEC-008]
status: verified
sources: [../../docs/03-prd.md, ../../docs/01-charter.md, ../006-consent/clarifications.md, ../006-consent/spec.md, ../007-agenda/clarifications.md, ../007-agenda/spec.md, ../008-booking/spec.md, ../009-move-cancel/spec.md, ../005-pseudonymized-log/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# reminders — Clarifications

The human answered every question on 2026-11-23 (see **Decisions**). The questions are kept
below as they were asked, each with the agent's proposal. **Where a decision differs from a
proposal, the decision prevails.**

**Id and folder (Q1):** **SPEC-009** in `specs/010-reminders/`. `specs/index.md` and SPEC-004 Q1
list reminders as the third follow-up of SPEC-004 ("proposed SPEC-009"), and the next free folder
number is 010.

## What the PRD, the charter and the earlier specs say

**What this spec is for:**

- **US-006** (reminder): "Given un paciente con una cita mañana a las 10:00 / When se ejecuta la
  tarea de recordatorios / Then el paciente recibe un mensaje con fecha, hora y dirección / And
  botones para confirmar asistencia o cancelar".
- **RF-006:** "enviar un recordatorio 24 h antes de cada cita con botones de confirmar o
  cancelar".
- **CONF-005 (open, DEP-04):** the director wants reminders for every patient; the GDPR needs
  consent before receiving messages. The proposal (a) is explicit consent in the first message
  of the bot. "No bloquea la defensa".
- **PRD §2 and charter §5:** at least 20 % fewer no-shows with reminders active (10 % today,
  about 25 empty slots a month).
- **PRD §7.8:** the bot sends no proactive messages except appointment reminders.
- **R-06:** GDPR with health data. Mitigation: explicit consent, minimal data, 30-day purge.

**What the earlier specs give or require:**

- **SPEC-004 Q8 (the agenda):** an appointment stores only the HMAC subject, the type and the
  times. "**The chat id for reminders** is decided in the reminders spec, with its own consent
  (CONF-005), in a **separate table**." An HMAC cannot be reversed, so the agenda alone can never
  write to the patient.
- **SPEC-006 (consent):**
  - consent covers **conversations**. "Whether consent to conversations also covers proactive
    messages is left to that spec [RF-006] and to DEP-04";
  - the consent record holds no `from.id` and no chat id; a withdrawal sets `revoked`, and
    rejections are not stored;
  - the HMAC key lives in the same database (`consent_key`) and must never be regenerated.
- **SPEC-007 (booking) and SPEC-008 (move and cancel):**
  - one future `booked` appointment per subject; `BOOKED_TEXT` and the «Mi cita» view carry
    «Cambiar» · «Anular» · «Hablar con recepción», with callbacks in the `bk:` namespace;
  - `agenda_cancel` and `agenda_move` (all or nothing; the old row gets `cancelled_at` and
    `replaced_by`); the minimum notice `change_min_lead` is 2 hours (example value);
  - withdrawing consent keeps the appointment and offers «Anular mi cita» (MC11), the only step
    allowed without consent;
  - A's keyboards are sent by «Responder reserva (1)…(6)»; never the whole keyboard in one
    expression (SPEC-007 R6).
- **SPEC-005 (privacy and logging):**
  - A saves no executions; only B's are kept, with `question` only, for 30 days;
  - **A's transient window:** n8n's local database holds a running execution, raw data included,
    for about 15 minutes;
  - B never receives `from.id` or a chat id (P5).
- **Infrastructure facts:**
  - n8n runs on the team's laptop, started with `n8n-start.ps1`, behind a Tailscale Funnel that
    only exposes `/webhook`. **When the laptop is off, nothing runs**, so a scheduled flow can
    miss its moment.
  - `n8n-start.ps1` does not set `GENERIC_TIMEZONE`, so a Schedule Trigger follows the machine's
    time zone. Due times are safer computed in SQL in Europe/Madrid, as the agenda already does.
  - In a private chat, Telegram's `chat.id` equals the user's `from.id`. **Storing the chat id
    means storing the Telegram user id**, a direct identifier that the agenda never kept.

## Coverage

**Proposed for this spec (SPEC-009):**

- consent for reminders, separate from the conversation consent, asked when booking;
- a separate table holding the chat id for each appointment that has a reminder, and its
  deletion rules;
- a new scheduled flow C that sends due reminders, exactly once, with no B and no Gemini;
- the reminder text and buttons, reusing the SPEC-008 «Cambiar» and «Anular» steps;
- what happens on move, cancel, consent withdrawal, a blocked bot and a missed run;
- the A changes to ask for the reminder and to stop it;
- new SQL functions, test-first on the test branch.

**Left for later specs:**

- **The reception panel** (RF-007): seeing confirmations and cancellations from reminders.
- **Reminders by other channels** (SMS, e-mail, WhatsApp): out of scope for v1.0 (PRD §7.4).
- **Several reminders per appointment** (for example a week and a day before), and reminders
  for appointments made by reception: the agenda only has the bot's.
- **Measuring the no-show rate** (PRD §2): the agenda does not record attendance; that is for
  the clinic's own records or the reception panel.
- **Hosting n8n on a server** (RES-05): needed for reminders that never miss a run.

## Decisions (human, 2026-11-23)

- **Q1 to Q15:** the proposals are accepted, with the details below.
- **Q3: the encryption key of the chat id in the same database is a known limitation**, like the
  HMAC key (SPEC-006). In production it would live outside the database.
- **Q6: «Iré» records the attendance confirmation on the appointment**, not on the reminder row,
  with no new patient data. It is an operational timestamp of the agenda, like `cancelled_at`
  (SPEC-008).
- **Q11: the SPEC-005 A4 exception is extended to A and C**, with the same conditions as in
  SPEC-006, SPEC-007 and SPEC-008:
  - fake ids;
  - one run per scenario;
  - `saveManualExecutions` disabled at the end;
  - **all pinned data removed and checked**;
  - the human deletes the executions.

  It is recorded in the SPEC-005 clarifications too.
- **Q11: the Telegram test** is done **in daytime** (outside 21:00–9:00 Madrid), **with n8n running**,
  on an appointment booked **more than 3 hours ahead**. The plan must take this into account.
- **A1–A4:** accepted as written.

## Questions, with the agent's proposals

- **Q1: Id and folder.**
  - Proposal: SPEC-009 in `specs/010-reminders/`, as above. PRD §11's RF-006 row ("Por escribir")
    gets SPEC-009.

- **Q2: Consent for reminders (CONF-005).**
  - Facts: SPEC-006 left open whether conversation consent covers proactive messages. A reminder
    is a message the patient did not ask for at that moment, and it needs a new identifier (the
    chat id). Both point to a separate, explicit choice.
  - Proposal: **a separate opt-in, asked once per appointment, right after booking.**
    - `BOOKED_TEXT` is followed by: «¿Quieres que te recuerde la cita el día antes por aquí?»,
      with «Sí, recuérdamela» · «No, gracias».
    - Only «Sí» stores anything (Q3). «No» stores nothing, as SPEC-006 does with rejections.
    - **The choice follows a move** (Q4): the patient is not asked again.
    - **The «Mi cita» view** shows the state: «Te recordaré la cita el día antes.» with «No quiero
      recordatorio», or, without one, «Recordármela el día antes». So a patient who said «No» can
      change their mind.
    - **The reminder itself** carries no «No quiero más recordatorios» button: with one
      appointment and one reminder, there is nothing left to stop once it is sent.
  - **Withdrawing the general consent** (SPEC-006): proactive messages need consent, so **the
    appointment's reminder is deleted** with its chat id, in the same step as the withdrawal. The
    appointment stays (SPEC-008 MC11). The withdrawal text adds «No te enviaré recordatorios.»
    when there was one.
  - Alternative: treat the conversation consent as covering reminders, and send one for every
    appointment. Simpler, but it is the option (b) of CONF-005 in disguise, and it stores a chat id
    the patient did not explicitly agree to.

- **Q3: How the chat id is stored.**
  - Proposal: **a separate table, `agenda_reminders`**, one row per appointment with a reminder:
    - `appointment_id` (references `agenda_appointments`, `ON DELETE CASCADE`), unique;
    - `chat_id_enc bytea`: the chat id **encrypted** with `pgp_sym_encrypt` (pgcrypto, already
      used for the HMAC), under a key in its own table `reminder_key`, generated inside Neon and
      never printed, like `consent_key`;
    - `due_at timestamptz` (24 hours before the start, Q7), `status` (`pending`, `sending`, `sent`,
      `skipped`, `failed`, `blocked`), `created_at` and `sent_at`;
    - no subject (it is reached through the appointment), no name, no type, no text.
  - **Honest limit:** the key is in the same database, as with the HMAC key (SPEC-006). Encryption
    protects against a dump of the table or a careless query, not against someone with full access
    to Neon. It is still better than plain text, at little cost.
  - Alternatives:
    - **plain chat id** with strict deletion: simpler, but one `SELECT` shows Telegram ids;
    - **the key outside the database** (an n8n credential passed to the query): stronger, but n8n
      would then hold the key in every query's parameters, and the transient window would show it.

- **Q4: When the chat id is deleted, and what happens to the row.**
  - Proposal: the chat id exists **only while a reminder is pending**:
    - **sent** → the chat id is wiped (`chat_id_enc = NULL`), and the row keeps `status = 'sent'`
      and `sent_at` until the appointment is purged (cascade, 30 days after its end);
    - **cancelled** (SPEC-008) → the row is deleted;
    - **moved** (SPEC-008) → the row **follows the new appointment**, with a new `due_at`. If the new
      appointment is less than 24 hours away, see Q7;
    - **the appointment passes** without a reminder sent → `skipped`, chat id wiped;
    - **consent withdrawn**, or **«No quiero recordatorio»** in the view → the row is deleted;
    - **the bot is blocked** (403, Q9) → `blocked`, chat id wiped.
  - **How, without touching the SPEC-008 functions:** a trigger on `agenda_appointments`, in the new
    SQL file. When a row becomes `cancelled`, it deletes its reminder, or, once `replaced_by` is set
    (a move), moves the reminder to the new appointment. `agenda_cancel` and `agenda_move` keep their
    code and their tests.

- **Q5: The reminder text.**
  - Facts: a notification shows the message on the lock screen, and US-006 asks for date, time
    and address. The appointment type is health data (SPEC-004 Q8).
  - Proposal: **generic, with no type:**
    - «Recordatorio de LifeCenter: tienes una cita mañana, {martes 1 de diciembre}, a las {9:00},
      en {dirección}. Si no puedes venir, puedes cambiarla o anularla aquí.»
    - The **address** is an example value until LifeCenter provides it (DEP-01), defined once and
      marked as example, like the urgency phone (SPEC-003). Is it in the knowledge base already?
      Proposal: a constant in the reminders module, with a test that it is marked as example.
    - The patient sees the type with «Ver mi cita» (the «Mi cita» view), inside the chat.
  - Alternative: include the type («tu limpieza»). It is more useful, but anyone who sees the
    phone learns it.

- **Q6: The reminder's buttons, and the 2-hour notice.**
  - Proposal: «Iré» · «Cambiar» · «Anular» · «Hablar con recepción».
    - **«Iré»** (US-006 «confirmar asistencia»): replies «Gracias, te esperamos.» and records
      `confirmed_at` on the reminder row, with no other data. It tells nobody yet (RF-007), but the
      reception panel can read it later. Alternative: reply only, store nothing.
    - **«Cambiar» and «Anular»**: exactly the SPEC-008 steps, with their buttons
      (`bk:x:<start>`, `bk:a:<start>`). They require consent, which the patient still has, or
      the reminder would have been deleted (Q2).
    - **The 2-hour notice** does not conflict: the reminder goes out about 24 hours before, so both
      buttons still work. A late reminder (Q7) is only sent while there are more than 2 hours left,
      so its buttons always work too.
  - The keyboard has 4 rows, within A's 1–6 (SPEC-008 MC29), but **C sends it**, so C needs its
    own Telegram node with 4 fixed rows and one expression per button field (SPEC-007 R6).

- **Q7: When it is sent.**
  - Proposal:
    - **due at 24 hours before the start**: `reminder_lead`, a new setting, 24 hours, example value;
    - **C runs every 15 minutes** (Schedule Trigger) and sends every reminder whose `due_at` has
      passed;
    - **quiet hours 21:00–9:00 Madrid**: nothing is sent at night. Because the clinic opens 9:00–20:00,
      a reminder 24 hours before always falls in daytime; quiet hours only matter for late ones;
    - **an appointment booked less than 24 hours ahead** (minimum 2 hours): the opt-in is still
      offered if it is at least 3 hours away, and the reminder is due **at once** (the next run).
      Otherwise the opt-in is not shown. Alternative: no reminder for appointments booked less
      than 24 hours ahead;
    - **n8n was off and the moment passed** (the laptop): C sends it late, on its next run, if the
      appointment is still more than `change_min_lead` (2 hours) away and it is daytime. Otherwise
      it marks the row `skipped` and wipes the chat id. A reminder is never sent after 21:00 or
      with less than 2 hours left.

- **Q8: Never twice.**
  - Proposal: **claim, then send**, in the database:
    - C's first query calls `reminder_claim_due(limit)`. In one statement it picks the due
      `pending` rows with `FOR UPDATE SKIP LOCKED`, sets them to `sending` with the claim time,
      and returns them with the decrypted chat id and the appointment's times;
    - two runs at the same time can never claim the same row;
    - after the Telegram call, C calls `reminder_mark(id, result)`: `sent` (chat id wiped), or
      `failed` / `blocked`;
    - **if C dies between the claim and the mark**, the row stays `sending`. It is **not retried**:
      a missed reminder is better than a duplicate. A `sending` row older than 1 hour is turned
      into `failed` by the next claim, and its chat id wiped.
  - Alternative: send first, then mark (at-least-once). A crash after sending would send it again.

- **Q9: A changed or cancelled appointment, and Telegram errors.**
  - Proposal:
    - **cancelled or moved** after the opt-in: handled by the trigger (Q4), so C never sees an
      old reminder. The claim also checks, in the same statement, that the appointment is still
      `booked` and in the future;
    - **403 «bot was blocked by the user»**, or the chat not found: `blocked`, chat id wiped, no
      retry;
    - **429 or a 5xx** (Telegram or network): `pending` again, to be retried by the next run while
      the window of Q7 is still open, at most 3 attempts; then `failed` and the chat id wiped;
    - the Telegram node has an error output, as the Postgres nodes do.

- **Q10: Where it lives.**
  - Proposal: **a new workflow C, `lifecenter-reminders`**:
    - Schedule Trigger (every 15 min) → «Reclamar recordatorios» (Postgres, `reminder_claim_due`) →
      «Componer recordatorio» (Code, the reminders module) → «Enviar recordatorio» (Telegram, 4
      fixed rows) → «Marcar recordatorio» (Postgres, `reminder_mark`), with error outputs;
    - **no B, no Gemini**: the text is fixed;
    - **C saves no executions** (none / none / false / false), like A, because they would hold the
      chat id. The SPEC-005 transient window applies, and is recorded as a limitation;
    - C has no webhook. It only talks to Neon and Telegram.
  - **The buttons of the reminder** arrive at A as normal callback queries, so A handles them.
    A changes too: the opt-in after `BOOKED_TEXT`, the «Mi cita» view's reminder line and button,
    «Iré», and the consent withdrawal (Q2).
  - Alternative: the schedule inside A. Not proposed: A would grow again, and it is the public
    webhook flow.

- **Q11: How it is tested without waiting 24 hours.**
  - Proposal:
    - **SQL:** pytest on the test branch with the `_at` versions and a fixed `p_now`: due rows,
      quiet hours, late ones, `skipped`, the claim under concurrency (two claims → each row once),
      the trigger on cancel and move, and the deletions;
    - **Node:** a reminders module with its test, like `citas.js` (texts, the date, the address
      marked as example, the buttons and the 64 bytes);
    - **A and C with pinned data**, under the SPEC-005 **A4 extension** (to be approved again):
      fake ids `9009xx`, one run per scenario, saving disabled at the end, every pinned datum
      removed and checked, the human deletes the executions. C's Telegram node is pinned, so no
      message is sent;
    - **the Telegram test**: the human books an appointment more than 3 hours ahead and says
      «Sí». The appointment is then within 24 hours, so it is due at once (Q7): C's next run sends
      it within 15 minutes, with no setting changed in `main`. The human then taps «Iré», and on a
      second appointment «Anular» from the reminder.
  - Alternative: a temporary `reminder_lead` of a few hours in `main`, with a before-and-after
    check. Not needed if the "booked within 24 hours" rule of Q7 is accepted.

- **Q12: New SQL functions.**
  - Proposal: a new file **`app/infra/sql/006_reminders.sql`**, idempotent, following SPEC-004:
    public functions without a time parameter, and `_at` versions with `p_now` for the tests.

    | Function | What it does |
    |---|---|
    | `reminder_key` setup | the key table and its one-off generation, never printed |
    | `reminder_set_at(from_id, start, chat_id, p_now)` / `reminder_set(…)` | the opt-in: creates or replaces the row for the subject's appointment at that start; `set`, `not_found` or `too_late` |
    | `reminder_clear(from_id, start)` | «No quiero recordatorio»: deletes the row; `cleared` or `not_found` |
    | `reminder_state(from_id)` | for the view and the withdrawal: whether the current appointment has a reminder |
    | `reminder_claim_due_at(limit, p_now)` / `reminder_claim_due(limit)` | Q8: claims the due rows and returns id, chat id, start and end |
    | `reminder_mark(id, result)` | `sent`, `failed`, `blocked` or `retry`, wiping the chat id when final |
    | `reminder_confirm(from_id, start)` | «Iré»: sets `confirmed_at` |
    | trigger on `agenda_appointments` | Q4: cancel deletes, move follows |
    | `consent_revoke` path | Q2: deleting the subject's reminders on withdrawal, from A's withdrawal step |

  - New settings in `agenda_settings`: `reminder_lead` (24 hours), `reminder_quiet_from` (21:00),
    `reminder_quiet_to` (9:00), all example values.
  - The functions return no subject, professional or room. Only the claim returns a chat id, and
    only to C.

- **Q13: Texts.** Proposed, all fixed:
  - **opt-in:** «¿Quieres que te recuerde la cita el día antes por aquí?» · «Sí, recuérdamela» ·
    «No, gracias»;
  - **after «Sí»:** «De acuerdo, te la recordaré el día antes.»; **after «No»:** «De acuerdo, no
    te enviaré recordatorio.»;
  - **the view:** «Te recordaré la cita el día antes.» · «No quiero recordatorio», or «Recordármela
    el día antes» when there is none;
  - **the reminder:** Q5;
  - **«Iré»:** «Gracias, te esperamos.»;
  - **the withdrawal with a reminder:** the SPEC-008 text plus «No te enviaré recordatorios.»;
  - **a reminder button on an appointment that is gone:** SPEC-008 `NOT_ACTIVE_TEXT`.

- **Q14: Order of work.**
  - Proposal, the same pattern as SPEC-007 and SPEC-008:
    1. preflight, read-only (hosts, «Neon main», A and B as published);
    2. the reminders module and the `citas.js` extension, test-first;
    3. `006_reminders.sql` on the test branch (key generation included), then `main` after the
       human confirms, with the before-and-after check;
    4. C built and A changed through the MCP, with pinned data (A4);
    5. the human publishes C and A and tests from Telegram;
    6. exports (C is new) and docs.

- **Q15: What is logged.**
  - Proposal: nothing new besides the reminder rows: their status, `sent_at` and `confirmed_at`
    are enough to count sent, confirmed, skipped and blocked reminders. They contain no chat id
    once final, and they go with the appointment after 30 days.

## Assumptions

- **A1:** private chats only, so the chat id is the user's id.
- **A2:** test accounts only, and the agenda's example data.
- **A3:** the laptop runs n8n during the demo. Reminders missed while it is off follow Q7.
- **A4:** one future appointment per patient, so one pending reminder per patient at most.

## Known limitations (expected)

- **The laptop:** reminders only go out while n8n runs. A server is needed for real use (RES-05).
- **The chat id is a direct identifier**, encrypted with a key in the same database (Q3).
- **C's transient window** (SPEC-005): n8n's local database briefly holds the running execution,
  chat id included.
- **The address is example data** until DEP-01.
- **«Iré» tells nobody** until the reception panel (RF-007).

## Dependencies and conditions

- **SPEC-004, SPEC-006, SPEC-007 and SPEC-008** implemented.
- **CONF-005 / DEP-04:** whether a separate opt-in is the consent LifeCenter's management wants,
  and the retention of the reminder rows.
- **DEP-01:** the clinic's address. **DEP-03:** the reminder lead and quiet hours.
- **AGENTS.md preflight:** the first task checks each credential's host.
- **Opening to real patients stays blocked**, for the reasons already listed in SPEC-004 to
  SPEC-008.
