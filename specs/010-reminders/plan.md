---
type: plan
spec_id: SPEC-009
title: reminders — Technical Plan
description: How to build reminders — read-only preflight (hosts, «Neon main», A and B as published, pgcrypto, no workflow C yet), recordatorios.js and the citas.js extension test-first, 006_reminders.sql (tables, key, trigger, claim) on the test branch then main, the new scheduled workflow C and A's changes through the MCP with pinned data, the daytime Telegram test, and exports and docs. B does not change.
tags: [plan, reminders, SPEC-009, n8n, neon]
status: verified
sources: [./spec.md, ./clarifications.md, ../009-move-cancel/plan.md, ../008-booking/plan.md, ../006-consent/plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# reminders — Plan

Same pattern as SPEC-007 and SPEC-008:

1. modules test-first in Node;
2. SQL test-first on the Neon test branch, then `main` after confirmation;
3. the workflows through the MCP with pinned data;
4. the human publishes and tests from Telegram;
5. exports and docs.

**B does not change.** A changes, and a new workflow **C** is created.

## Architecture

What changes in A is marked `+` or `~`.

```text
A  lifecenter-telegram-demo (saves NO executions)
   … → Decidir → ¿Qué hacer?
        ├─ booking → Preparar reserva (~ citas.js: reminder steps ry / rn / rq / i)
        │             → ¿Qué consulta? (+ output reminder)
        │                 ├─ agenda   → Consultar agenda (~ also returns has_reminder)
        │                 ├─ book     → Reservar         (unchanged; compose adds the opt-in)
        │                 ├─ reminder → + Recordatorio   (reminder_set / _clear / _confirm,
        │                 │                               plus my_next and has_reminder)
        │                 └─ cancel, move, none (unchanged)
        │             → Componer reserva (~ citas.js: opt-in, view lines, reminder texts)
        └─ withdraw → Guardar retirada → Cita tras retirar (~ also reminder_forget → had_reminder)
                                       → Componer retirada (~ adds «No te enviaré recordatorios.»)

C  lifecenter-reminders (new; saves NO executions; no webhook)
   Schedule Trigger (every 15 min)
     → Reclamar recordatorios (Postgres: reminder_claim_due(20); 0..n rows, chat id decrypted)
     → Componer recordatorio  (Code: recordatorios.js, text + 4 buttons)
     → Enviar recordatorio    (Telegram, 4 fixed rows, error output)
          ├─ ok    → Marcar recordatorio (Postgres: reminder_mark(id, 'sent'))
          └─ error → Clasificar error (Code: 403 / chat not found → blocked; 429 / 5xx → retry)
                     → Marcar recordatorio

Neon: 006_reminders.sql → agenda_reminders, reminder_key, attendance_confirmed_at,
      reminder_lead / quiet hours, reminder_* functions, the move/cancel trigger
```

The buttons of the reminder (`bk:i`, `bk:x`, `bk:a`, `handoff`) arrive at A like any other
callback query. C only sends.

## Step 0: Preflight, read-only (RM32, AGENTS.md)

**The agent, with read-only access only. Nothing is created or changed.**

- **Neon, on both branches:**
  - the shortened hosts and branch ids;
  - the `pgcrypto` extension is installed, since `pgp_sym_encrypt` depends on it;
  - the SPEC-004, SPEC-007 and SPEC-008 functions exist;
  - `agenda_reminders`, `reminder_key`, `attendance_confirmed_at`, the three settings and the
    `reminder_*` functions **do not exist yet**;
  - appointments by status, `consent` by status, and `consent_key` rows, with no subject or key
    printed.
- **The `Neon main` credential:** its `updatedAt` in n8n's local database (metadata only). If it
  is still 22/11/2026 16:02 UTC (SPEC-006 K5), the human need not check it in the UI. Otherwise,
  the human checks it there before anything else.
- **Workflows:**
  - A (`q3f5dVrl8OUsXJrG`) and B (`v7Bxk8HuE4GQ3lBl`) active, with draft = published = the export in
    git (A `7c3d4100…`, B `0b3cb06d…`);
  - their settings, no pinned data, and no saved execution of A;
  - **no workflow C exists yet**: the MCP `search_workflows` finds no `lifecenter-reminders`, and
    n8n's local database has no workflow with that name;
  - the Telegram credential `VzY1vvAFNqi3JSKT` exists, since C uses it.

## Step 1: The JavaScript modules, test-first (RM1–RM6, RM18–RM20, RM27, RM28)

**`n8n/code/recordatorios.js` (new)**, carried by C's «Componer recordatorio»:

- `REMINDER_TEXT`, `CLINIC_ADDRESS` (example value, with a flag `CLINIC_ADDRESS_IS_EXAMPLE`
  like `urgencias.js`), the button labels;
- `whenText(start, now)`: «mañana, martes 1 de diciembre», «hoy, …», or the full date;
- `composeReminder(row, now)` → `{ text, rows }`, with the buttons «Iré» (`bk:i:<start>`),
  «Cambiar» (`bk:x:<start>`), «Anular» (`bk:a:<start>`) and «Hablar con recepción»;
- `classifySendError(error)` → `blocked` (403, "chat not found") or `retry` (429, 5xx, network).

It reuses no code from `citas.js`: it is a separate module with its own small date helper and
its own sync check. It is simpler than splitting `citas.js`.

**`n8n/code/citas.js`, extended:**

- callbacks `bk:ry`, `bk:rn`, `bk:rq` and `bk:i`, with their start code;
- `prepare`: the steps `reminder_on`, `reminder_off`, `reminder_clear` and `attend`. All except
  `reminder_off` use a new query, `reminder`. All require consent (RM6);
- `compose`:
  - the opt-in after `BOOKED_TEXT` when the appointment is at least 3 hours away;
  - the view's reminder line and button (from `has_reminder`);
  - `REMINDER_SET_TEXT`, `REMINDER_OFF_TEXT` and `ATTENDANCE_TEXT`;
  - `NOT_ACTIVE_TEXT` for a reminder button on an appointment that is gone;
- `revokedReply(…, hadReminder)` adds `REMINDER_WITHDRAWN_LINE`.

**`consentimiento.js`:** no change. The reminder callbacks are `bk:` buttons that need consent,
which is the default.

**Tests, written first:**

- **`n8n/code/recordatorios.test.js`:**
  - the texts, and `CLINIC_ADDRESS` marked as example;
  - `whenText` for tomorrow, today and later, across both DST changes;
  - the 4 buttons and the 64 bytes;
  - `classifySendError` on real Telegram error messages;
  - a sync check with C's export, skipped «hasta N4».
- **`n8n/code/citas.test.js`:**
  - the new callbacks;
  - every `prepare` and `compose` case of the reminder steps, with and without consent;
  - the opt-in window (2 h 59 min → no offer; 3 h → offer);
  - the view lines;
  - the withdrawal line;
  - keyboards of 1–6 rows (the booked message with the offer has 5).

  The expected `BOOKED_TEXT` cases change, because they gain the offer. They go red first.
- Red first with modules that only gain their texts; then green. `consentimiento.test.js` and
  `urgencias.test.js` must stay green. The `citas.js` sync check is skipped «hasta N4».

## Step 2: `006_reminders.sql` on the test branch [asks for confirmation first] (RM7–RM17, RM19, RM24–RM26, RM29)

- **Schema**, all `IF NOT EXISTS`:
  - `reminder_key (key bytea)`, one row, generated with `gen_random_bytes(32)` only if empty.
    Never selected by any function that returns it;
  - `agenda_reminders`:
    - `id`;
    - `appointment_id` (unique, `ON DELETE CASCADE`);
    - `chat_id_enc bytea`;
    - `due_at`, `status` (`pending`, `sending`, `sent`, `skipped`, `failed`, `blocked`);
    - `attempts`, `claimed_at`, `sent_at`, `created_at`;
  - `agenda_appointments.attendance_confirmed_at timestamptz`;
  - `agenda_settings.reminder_lead` (24 h), `reminder_quiet_from` (21:00) and `reminder_quiet_to`
    (9:00).
- **Functions** (each `_at` with `p_now`, and the public one with `now()`):
  - **`reminder_set`:**
    - finds the subject's `booked` appointment at that start, still in the opt-in window;
    - upserts its row with the encrypted chat id, `due_at = greatest(start - reminder_lead,
      p_now)` and `pending`;
    - returns `set`, `not_found` or `too_late`.
  - **`reminder_clear`:** deletes the row; returns `cleared` or `not_found`.
  - **`reminder_state(from_id)`:** `has_reminder` for the current appointment.
  - **`reminder_forget(from_id)`:** deletes the subject's reminders; returns `had_reminder`.
  - **`reminder_confirm`:** sets `attendance_confirmed_at` once; returns `confirmed`,
    `already` or `not_found`.
  - **`reminder_claim_due(limit)`:**
    1. turns `sending` rows older than 1 hour into `failed`, with no chat id;
    2. marks `skipped`, with no chat id, the `pending` rows whose window has closed: less than
       `change_min_lead` left, the appointment past or not `booked`, or no consent in force for the
       decrypted chat id;
    3. claims, with `FOR UPDATE SKIP LOCKED`, the `pending` rows that are due, outside quiet hours
       (Madrid) and inside the window;
    4. sets them to `sending`, adds 1 to `attempts`;
    5. returns `id`, `chat_id` (decrypted), `starts_at` and `ends_at`.
  - **`reminder_mark(id, result)`:**
    - `sent`: chat id wiped, `sent_at`;
    - `blocked`: chat id wiped;
    - `retry`: back to `pending` if fewer than 3 attempts, otherwise `failed` with the chat id
      wiped.
- **Trigger** `AFTER UPDATE OF status, replaced_by ON agenda_appointments`:
  - a row that becomes `cancelled` without `replaced_by` → delete its reminder;
  - a row whose `replaced_by` is set → move its reminder to the new appointment, with a new
    `due_at` and `pending`.

  This works with SPEC-008's two updates (cancel first, then `replaced_by`): the first update
  must **not** delete the reminder when a move is in progress.
  - **Decision (human, plan review, 2026-11-23): a constraint trigger `DEFERRABLE INITIALLY
    DEFERRED`**, which runs at the **end of the transaction**. By then a move has set
    `replaced_by`, so the reminder moves to the new appointment. A cancellation still has
    `replaced_by = NULL`, so the reminder is deleted.
  - The other option, deciding at the first update, is rejected. In `agenda_move` the first
    update cancels the old row while `replaced_by` is still `NULL`, so it would delete the
    reminder before the move sets it.
  - The N2 tests must show both cases through the real `agenda_move` and `agenda_cancel`:
    - a move keeps one reminder, now on the new appointment with its new `due_at`;
    - a cancellation leaves none;
    - a move that ends in `taken` (rolled back) leaves the reminder on the old appointment,
      unchanged.

    `agenda_cancel` and `agenda_move` do not change.
- **`tests/infra/test_reminders_sql.py`**, written first, with fake ids `9009xx` and dates from
  today. It covers every case of the spec's acceptance criteria, including:
  - two concurrent claims;
  - the encrypted column never containing the chat id in clear text;
  - no function returning the key.
- **Run order:**
  1. red, with nothing created;
  2. show the SQL, the commands and the host, and wait;
  3. the schema;
  4. green;
  5. all of `tests/infra`.

## Step 3: `main` [asks for confirmation first] (RM29)

The read-only check before and after, as in SPEC-008 M3. It prints counts and yes/no only:

- `kb_fragments`, `consent` and `consent_key` unchanged;
- the agenda configuration unchanged, plus the three new settings;
- the appointments unchanged in their old columns, with `attendance_confirmed_at` empty;
- every earlier public function unchanged;
- the new tables, the trigger and the new functions created;
- `reminder_key` with 1 row (never printed).

**Stop if** anything that must not change has changed.

## Step 4: C and A through the MCP, with pinned data (RM1–RM23, RM30)

**Before changing anything, list the nodes to add, change and rewire, and wait.**

- **C (new):**
  - built with the Workflow SDK through the MCP (`get_workflow_sdk_reference`, then
    `validate_workflow` and `create_workflow_from_code`);
  - settings none / none / false / false, as for A;
  - not published by the agent.
- **A:**
  - «Preparar reserva», «Componer reserva», «¿Es una reserva?» and «Componer retirada» carry the
    new `citas.js`;
  - «¿Qué consulta?» gains `reminder`;
  - the new Postgres node «Recordatorio» (error output);
  - «Consultar agenda» also returns `has_reminder`;
  - «Cita tras retirar» also calls `reminder_forget`.

  The structural check uses a CLI export, as in SPEC-008 M4.
- **Queries first on the test branch,** with fake ids and cleanup, as in SPEC-008 M4.
- **Pinned runs** (A4 extension; ids `900951…`; C's Telegram node pinned, so nothing is sent):
  - **A:**
    - the offer after booking, at 3 h and at 2 h 59 min;
    - «Sí», «No», «No quiero recordatorio»;
    - the view with and without a reminder;
    - «Iré», twice, and on an old appointment;
    - every reminder step without consent;
    - the withdrawal with and without a reminder, and with the lookup failing;
    - a Neon failure in «Recordatorio».
  - **C:**
    - nothing due;
    - one due → sent → `sent`;
    - two due;
    - 403 → `blocked`;
    - 429 → `retry`;
    - a Neon failure in the claim and in the mark;
    - the message checked for no type and 4 buttons.
- **Afterwards:**
  - `saveManualExecutions: false` in A and C, read back;
  - no pinned data in A, B or C;
  - B intact;
  - the exact list of executions for the human to delete.

## Step 5: Publish and test from Telegram [human] (RM31)

- The human publishes **C first** (inert while there are no reminders), then **A**.
- **Conditions (decision Q11):** in daytime, outside 21:00–9:00 Madrid, with n8n running.
- **The test:**
  1. book an appointment more than 3 hours ahead, and tap «Sí, recuérdamela»;
  2. within 15 minutes C sends the reminder, due at once by RM14;
  3. check the text, then tap «Iré»;
  4. book or move another appointment to see that the reminder follows a move;
  5. cancel one to see it deleted;
  6. tap «No, gracias» on another booking.
- **The agent checks, read-only, with no subject or chat id printed:**
  - the reminder rows' status, `sent_at` and that the chat id is `NULL` once final;
  - `attendance_confirmed_at`;
  - that C saved no execution and A none after the transient window;
  - that B received only `question`.

## Step 6: Exports and docs (RM33)

- Export A and C from their published versions, without `shared` and `pinData`. C is a new file,
  `n8n/workflows/lifecenter-reminders.json`. B is unchanged: check that its export equals git.
- Run the scan, including both full Neon hosts, every Node test with its sync checks, and
  `pytest`.
- Docs:
  - README: a "Reminders (SPEC-009)" section, how to start C, the settings and the limitations;
  - `specs/index.md`;
  - spec, plan and tasks marked implemented.

## Requirement → component map

| Requirement | Component |
|---|---|
| RM1–RM6 | `citas.js` (`prepare` / `compose`), «Recordatorio» → `reminder_set` / `reminder_clear`, «Consultar agenda» (`has_reminder`) |
| RM7–RM11 | `006_reminders.sql`: tables, key, the trigger |
| RM12 | «Cita tras retirar» → `reminder_forget`, «Componer retirada» |
| RM13–RM18 | C: Schedule → `reminder_claim_due` → `recordatorios.js` → Telegram → `reminder_mark` |
| RM19, RM20 | «Iré» → `reminder_confirm`; «Cambiar» / «Anular» are SPEC-008 |
| RM21–RM23 | C's settings and nodes; no B, no Gemini, no log table |
| RM24–RM26 | `006_reminders.sql`, `test_reminders_sql.py` |
| RM27, RM28 | `recordatorios.js`, `recordatorios.test.js`, `citas.test.js` |
| RM29–RM33 | Steps 0, 2–6 |
