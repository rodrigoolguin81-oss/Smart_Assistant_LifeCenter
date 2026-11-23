---
type: plan
spec_id: SPEC-008
title: move and cancel — Technical Plan
description: How to build moving and cancelling from Telegram — read-only preflight (credential hosts, «Neon main», the state of A and B), citas.js and consentimiento.js extended test-first, 005_move_cancel.sql (agenda_cancel, agenda_move, two columns and a setting) on the test branch then main, A's new steps through the MCP with pinned data (a sixth keyboard node, the withdrawal reply), the Telegram test, and exports and docs. B does not change.
tags: [plan, move, cancel, SPEC-008, n8n, neon]
status: implemented
sources: [./spec.md, ./clarifications.md, ../008-booking/plan.md, ../007-agenda/plan.md, ../006-consent/plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# move and cancel — Plan

Same pattern as SPEC-007: modules test-first in Node, SQL test-first on the Neon test branch,
then `main` after confirmation, then flow A through the MCP with pinned data, then the human
publishes and tests from Telegram. **B does not change** (MC25), so only A is published.

## Architecture

What changes in A is marked `+` or `~`. Every other node stays as it is.

```text
A  lifecenter-telegram-demo (saves NO executions)
   Telegram Trigger → Clasificar (~ consentimiento.js: decide() lets bk:a, bk:ac and bk:v:<start>
                                   through without consent, flagged consent: false)
     → ¿Qué ha llegado?  (unchanged: every bk: is already a booking_button)
         → Consultar consentimiento → Decidir → ¿Qué hacer?
              ├─ core     → ¿Es una reserva? (~ citas.js: textIntentFor → change | booking | none)
              │               ├─ change or booking → Preparar reserva
              │               └─ none              → Llamar al núcleo → B (unchanged)
              ├─ booking  → Preparar reserva (~ citas.js prepare: the change steps)
              │               → ¿Qué consulta? (+ outputs cancel, move)
              │                   ├─ none   ───────────────────────────────────────┐
              │                   ├─ agenda → Consultar agenda (~ type of my appt) ┤ (each with
              │                   ├─ book   → Reservar                             ┤  an error
              │                   ├─ cancel → + Anular cita  (agenda_cancel)       ┤  output
              │                   └─ move   → + Mover cita   (agenda_move)         ┤  → D7)
              │                                                                    ▼
              │                        Componer reserva (~ citas.js compose: the change texts)
              ├─ withdraw → Guardar retirada
              │               ├─ ok    → + Cita tras retirar (agenda_my_next, error output)
              │               │            → + Componer retirada (citas.js: revokedReply)
              │               └─ error → Tras guardar (D7, unchanged)
              ├─ accept / reply (unchanged)
          → ¿Qué teclado? → booking → ¿Cuántos botones? (+ rule 6) → Responder reserva (1)…(6)
                                                                      (+ «Responder reserva (6)»)

Neon: 005_move_cancel.sql → agenda_cancel(_at), agenda_move(_at),
      agenda_appointments.cancelled_at / replaced_by, agenda_settings.change_min_lead
```

No change step goes through B. Every query goes from A straight to Neon with `from.id` as a
parameter (MC25).

## Step 0: Preflight, read-only (MC32, AGENTS.md)

**The agent, with read-only access only. Nothing is created or changed.**

- **`.env` hosts:** print the hosts of `DIRECT_URL` and `TEST_DATABASE_URL`, shortened as
  `ep-…-…`, and their `neon.branch_id`. They must differ, and be two branches of the same
  project.
- **Neon, on both branches:**
  - the 7 SPEC-004 functions and the 2 SPEC-007 functions exist;
  - `agenda_cancel*` and `agenda_move*` do not exist yet;
  - the columns `cancelled_at`, `replaced_by` and `change_min_lead` do not exist yet;
  - the agenda configuration is 3 / 3 / 5 / 11 / 1;
  - appointments by status and by past or future, with no subject printed. `main` has the demo
    appointment of 23/11/2026 9:00, which is now past. The test branch has 0;
  - `consent` rows by status, and `consent_key` 1 row, with no subject or key printed.
- **The `Neon main` credential:**
  - the MCP's `list_credentials`: name, type and id (`QvG6Gru4fDSLvtzu`);
  - n8n's local database, metadata only: its `updatedAt`, compared with the SPEC-006 K5 fix
    (22/11/2026 16:02 UTC). No credential data is read;
  - **the human, in the n8n UI, without saving:** open «Neon main» and check that **Host** is
    `ep-steep-resonance-…` (the host of `DIRECT_URL`, not the test branch's `ep-blue-firefly-…`),
    Database `neondb`, User `neondb_owner`, SSL `require`, and **the three certificate fields
    empty**. Close it without saving, and report what was seen.
- **Workflows:**
  - A (`q3f5dVrl8OUsXJrG`) and B (`v7Bxk8HuE4GQ3lBl`) are active. Draft = published = the
    `versionId` of the exports in git (A `6a033c75…`, 35 nodes; B `0b3cb06d…`, 11 nodes),
    compared node by node with `workflow_history`;
  - A's settings: none / none / false / false. B's: saves everything, with the caller policy
    limited to A;
  - no pinned data in A or B;
  - no saved execution of A; the B executions that exist (count and dates only).
- Check: the findings are recorded in tasks M0, and nothing was created or changed.

## Step 1: The JavaScript modules, test-first (MC1–MC20, MC27–MC29)

**`n8n/code/citas.js`, extended:**

- **Texts:** the new texts of the spec, the three changed SPEC-007 texts, and the "without
  consent" variants. `{plazo}` is built from `change_min_lead` in minutes («2 horas»).
- **Codec:** `cb()` and `parseBookingCallback()` learn the change callbacks: `bk:v`,
  `bk:v:<start>`, `bk:a:<start>`, `bk:ac:<start>`, `bk:x:<start>`, `bk:xm:<start>:<from>`,
  `bk:xs:<start>:<new>` and `bk:xc:<start>:<new>`. They carry no type. A malformed one gives
  `malformed`, which opens the menu as in SPEC-007 BK14.
- **Phrases:** `detectChangePhrase(text)`, a strict list on the normalized, pseudonymized text,
  like `detectBookingPhrase`. `textIntentFor(question, urgency)` replaces `bookingPhraseFor` in
  «¿Es una reserva?»:
  - an urgency → no intent;
  - a change phrase → `{ match: true, intent: 'change' }`;
  - a booking phrase → `{ match: true, intent: 'booking', type, requestOnly }`;
  - otherwise → `{ match: false }`.

  `bookingPhraseFor` stays exported, unchanged, so the SPEC-007 tests keep passing.
- **`prepare(route, phrase, now, consent)`:** new steps, each with its single query:

  | Step | From | Query |
  |---|---|---|
  | `view` | a change phrase, `bk:v` | `agenda` (the current appointment) |
  | `cancel_confirm` | `bk:a:<start>` | `agenda` (does it still exist? too late?) |
  | `cancel` | `bk:ac:<start>` | `cancel` |
  | `keep` | `bk:v:<start>` | `agenda` with consent, `none` without |
  | `move_slots` | `bk:x:<start>` | `agenda`, slots of the appointment's type from now |
  | `move_more` | `bk:xm:<start>:<from>` | `agenda`, slots after `<from>` |
  | `move_confirm` | `bk:xs:<start>:<new>` | `agenda` (does it still exist? too late?) |
  | `move` | `bk:xc:<start>:<new>` | `move` |

  Without consent, only `cancel_confirm`, `cancel` and `keep` are possible (decide() lets
  nothing else through).
- **`compose(prep, db, now)`:** a text and the keyboard rows for every step and result:
  - the «Mi cita» view;
  - `CANCEL_CONFIRM_TEXT`, or `TOO_LATE_TEXT`, or `NOT_ACTIVE_TEXT` + view when the appointment
    at the start is gone;
  - the move slots, **with the current start filtered out**;
  - every `agenda_cancel` and `agenda_move` result;
  - the "without consent" variants.
  - The three changed SPEC-007 texts get «Cambiar» · «Anular» · «Hablar con recepción».
- **`revokedReply(revokedText, myNext, lookupFailed)`**, for «Componer retirada»: returns
  `REVOKED_TEXT`, `REVOKED_WITH_APPOINTMENT_TEXT` with «Anular mi cita», or
  `REVOKED_LOOKUP_FAILED_TEXT`.

**`n8n/code/consentimiento.js`, extended:**

- `decide()`: a `booking_button` whose data is `bk:a:<start>`, `bk:ac:<start>` or `bk:v:<start>`
  gives `{ action: 'booking', consent: false }` when there is no consent in force. Every other
  booking step without consent still gets the notice. With consent, `consent: true`.
- A failed consent lookup still gives D7, for every step.

**Tests, written first:**

- **`n8n/code/citas.test.js`:**
  - every change callback, the round trip, and the 64-byte limit;
  - **`evals/change_phrases.yaml`**: about 20 positives and 20 negatives, including the spec's
    («me cambiaron la cita», «¿se puede cancelar sin coste?», «¿cuánto cuesta cancelar?», «la
    cita de mi madre», «¿a qué hora es mi cita?»). Every positive must match, and 0 negatives
    may;
  - **the SPEC-007 booking dataset**, run again: the same 25/25 positives and 0/25 negatives;
  - **the order:** urgency + change → urgency, change + booking words → change (for example
    «quiero cambiar la cita que pedí»), and booking → booking;
  - every `prepare` and `compose` case of the new steps, with and without consent;
  - **the expected text of the existing SPEC-007 cases changes** for `BOOKED_TEXT`, `LIMIT_TEXT`
    and `MY_APPOINTMENT_TEXT` (spec, changed texts). They go red first, like the rest;
  - every keyboard has **1 to 6 rows** of one button (the R6 test, extended);
  - the sync check with «¿Es una reserva?», «Preparar reserva», «Componer reserva» and the new
    «Componer retirada».
- **`n8n/code/consentimiento.test.js`:** the three buttons allowed without consent, the others
  refused, and the sync check with «Clasificar» and «Decidir».
- **Red first:** the tests, plus modules that only gain their new constants. Then the functions,
  until green. `urgencias.test.js` must stay green.

## Step 2: `005_move_cancel.sql` on the test branch [asks for confirmation first] (MC21–MC23, MC30)

- **Schema changes,** all `IF NOT EXISTS`:
  - `agenda_appointments.cancelled_at timestamptz` and `replaced_by uuid REFERENCES
    agenda_appointments (id) ON DELETE SET NULL`. Both are empty on the existing rows;
  - `agenda_settings.change_min_lead interval NOT NULL DEFAULT interval '2 hours'`, which fills
    the existing row. The row is already `ejemplo = true`.
- **`agenda_cancel_at(p_from_id, p_start, p_now)`:**
  1. purge, compute the subject, take the subject's advisory lock (the same key as
     `agenda_book`);
  2. find the subject's `booked` row with `starts_at = p_start` and `starts_at > p_now`, `FOR
     UPDATE`. None → `not_found`;
  3. `starts_at < p_now + change_min_lead` → `too_late`, with the type and the times;
  4. set `status = 'cancelled'` and `cancelled_at = p_now` → `cancelled`, with the type and the
     times.
- **`agenda_move_at(p_from_id, p_old_start, p_new_start, p_now)`:**
  1. purge, subject, lock; find the old row as above → `not_found`; `too_late`;
  2. `p_new_start = p_old_start` → `invalid` / `same_slot`. `agenda_slot_problem(type,
     p_new_start, p_now)` → `invalid` with its reason;
  3. **inside one `BEGIN … EXCEPTION` block** (a subtransaction):
     - set the old row `cancelled`, `cancelled_at = p_now`;
     - try each professional of the role and each room, as `agenda_book_at` does, each insert in
       its own inner block that catches `exclusion_violation`;
     - on the first success, set the old row's `replaced_by` → `moved`, with the old and the new
       times;
     - if no pair is free, raise a private exception. The outer block catches it, **which rolls
       back the cancellation**, and returns `taken`. The old row is `booked` and unchanged.
  - The limit check is not run: the move keeps the subject at one future appointment, and the
    lock serializes it with `agenda_book`.
- **Public versions** `agenda_cancel(from_id, start)` and `agenda_move(from_id, old_start,
  new_start)`, which call the `_at` versions with `now()`.
- **`tests/infra/test_move_cancel_sql.py`**, written first, on the test branch only, with fake
  ids `9008xx` and dates computed from today. Each test cleans up. It covers:
  - every result of both functions, and that the losing results change nothing (the old row is
    compared before and after);
  - the slot freed by a cancel is offered again;
  - a move 15 minutes later with the same professional;
  - **concurrency**, with threads and separate connections, as in SPEC-004:
    - two patients moving into the same free slot → 1 `moved`, 1 `taken`;
    - a move and an `agenda_book` of the same subject → 1 `moved`, 1 `limit`;
    - two «Sí, anular» → 1 `cancelled`, 1 `not_found`;
  - the public signatures have no time parameter, and return no professional, room, subject or
    id;
  - every session time zone;
  - re-applying the schema leaves `kb_fragments`, `consent`, the key and the agenda rows
    unchanged, and the new columns empty on the old rows.
- **Run order:** red, with nothing created (the reapply and file-exists tests are excluded) →
  show the SQL, the exact commands and the host, and wait → the schema → green → all of
  `tests/infra`.

## Step 3: `main` [asks for confirmation first] (MC30)

The same read-only check, before and after, as SPEC-007 R3. It prints only counts, existence and
fingerprints compared inside the script:

- `kb_fragments` rows and md5;
- `consent` and `consent_key` unchanged;
- the agenda configuration unchanged, plus `change_min_lead` = 2 hours afterwards;
- the appointments unchanged, with the new columns empty;
- 4 new functions.

**Stop if** anything that must not change has changed.

## Step 4: A through the MCP, with pinned data (MC1–MC20, MC24–MC29, MC31)

**Before changing anything, list the nodes to add, change and remove, and wait.**

**Nodes:**

- **changed:**
  - «Clasificar» and «Decidir»: the extended `consentimiento.js`;
  - «¿Es una reserva?», «Preparar reserva» and «Componer reserva»: the extended `citas.js`.
    «¿Es una reserva?» calls `textIntentFor`. «Preparar reserva» passes the consent flag from
    «Decidir»;
  - «¿Qué consulta?»: two more outputs, `cancel` and `move`;
  - «Consultar agenda»: when the step has no type (`view`, the confirmations, the move slots),
    the slots use the type of the current appointment. It also returns `change_min_lead` in
    minutes. Still one row always, with its error output;
  - «¿Cuántos botones?»: a sixth rule;
- **new:**
  - «Anular cita» (Postgres on `Neon main`, error output): `agenda_cancel`, plus the current
    appointment on `not_found`, in one statement that always returns one row;
  - «Mover cita» (Postgres, error output): `agenda_move`, plus the next slots of the type on
    `taken` and `invalid`, and the current appointment on `not_found`, in one statement;
  - «Cita tras retirar» (Postgres, error output): `agenda_my_next`. It runs only on «Guardar
    retirada»'s success output;
  - «Componer retirada» (Code, `citas.js`): `revokedReply`;
  - «Responder reserva (6)» (Telegram): 6 fixed rows, one expression per button field, exactly
    like «(1)»–«(5)»;
- **rewired:** «Guardar retirada»'s success output goes to «Cita tras retirar» instead of «Tras
  guardar». Its error output still goes to «Tras guardar» (D7).
- **Unchanged:** everything else, B, and A's settings (MC26).

**Pinned runs** (approved A4 extension; fake ids `900801…`; one run per scenario). Trigger,
Telegram, consent and agenda nodes pinned:

- with consent:
  - `/micita` with an appointment → the view with «Cambiar» and «Anular»;
  - a change phrase → the view; with no appointment → `NO_APPOINTMENT_TEXT`;
  - urgency + change phrase → B → urgency; a change phrase negative → B;
  - «Anular» → confirmation; too late → `TOO_LATE_TEXT`; gone → `NOT_ACTIVE_TEXT` + view;
  - «Sí, anular» → `cancelled`, `too_late`, `not_found`;
  - «Mantener mi cita» (`bk:v` and `bk:v:<start>`) → `KEPT_TEXT` + view;
  - «Cambiar» → 6 rows, current start filtered out; no other slots → `MOVE_NO_SLOTS_TEXT`;
  - «Ver más» while moving; a slot → `MOVE_CONFIRM_TEXT`;
  - «Confirmar cambio» → `moved`, `taken` + slots, `invalid` + slots, `too_late`, `not_found`;
  - `BOOKED_TEXT` and `LIMIT_TEXT` with the new buttons;
  - a Neon failure in «Consultar agenda», «Anular cita» and «Mover cita» → D7;
- without consent:
  - «Anular», «Sí, anular» and `bk:v:<start>` work, with the "without consent" texts;
  - `bk:v`, «Cambiar», «Confirmar cambio» and a change phrase → the notice;
- the withdrawal: with an appointment → `REVOKED_WITH_APPOINTMENT_TEXT` + «Anular mi cita»;
  without → `REVOKED_TEXT`; a failure in «Cita tras retirar» → `REVOKED_LOOKUP_FAILED_TEXT`; a
  failure in «Guardar retirada» → D7.

Each run checks the path, the text, the keyboard (rows and `callback_data` ≤ 64 bytes) and the
chat id, and that **B is called only** in the urgency and negative-phrase runs.

**Afterwards:** `saveManualExecutions: false`, read back; **no pinned data** in A, checked with
`get_workflow_details` and a CLI export; the settings as before; the list of executions for the
human to delete.

## Step 5: Publish and test from Telegram [human]

The human publishes **A only**, then follows the spec's Telegram acceptance list. The demo
appointment of 23/11 is past, so the test starts with `/cita` and a new booking.

The agent checks, read-only and without printing any subject:

- `agenda_appointments` on `main`: status, type, times, and whether `cancelled_at` and
  `replaced_by` are set;
- B's executions: none for change steps, and only `question` in the others;
- that A has no saved execution left after about 15 minutes (SPEC-005 window).

## Step 6: Exports and docs (MC33)

- Export A from its published version, with draft = published checked, and `shared` and `pinData`
  removed. B is not re-exported, because it did not change; check that its export in git is still
  its published version.
- Run the scan, the three Node tests with every sync check, and `pytest`.
- README: a "Changing and cancelling (SPEC-008)" subsection, the «Try it» rows, the minimum
  notice and where to change it, what happens on withdrawal, and the limitations.
- `specs/index.md`, and spec, plan and tasks marked implemented.

## Requirement → component map

| Requirement | Component |
|---|---|
| MC1, MC2 | `compose` (changed SPEC-007 texts with the buttons) |
| MC3–MC5 | «Detectar urgencia» → «Decidir» → «¿Es una reserva?» (`textIntentFor`) → «Preparar reserva» |
| MC6–MC9 | `prepare` / `compose`, «Consultar agenda», «Anular cita» → `agenda_cancel` |
| MC10 | `consentimiento.js` `decide()`, `compose` without consent |
| MC11, MC12 | «Guardar retirada» → «Cita tras retirar» → «Componer retirada» (`revokedReply`) |
| MC13–MC16 | «Consultar agenda» (type of the appointment), «Mover cita» → `agenda_move` |
| MC17–MC20 | the start in every button; `agenda_cancel` / `agenda_move` (`not_found`, `too_late`, `same_slot`); `change_min_lead` |
| MC21–MC23 | `005_move_cancel.sql`, `test_move_cancel_sql.py` |
| MC24 | the error outputs of «Consultar agenda», «Anular cita», «Mover cita» and «Cita tras retirar» |
| MC25, MC26 | no change path through B; A's settings; no new table |
| MC27–MC29 | `citas.test.js`, `consentimiento.test.js`, `evals/change_phrases.yaml`; «Responder reserva (6)» |
| MC30–MC33 | Steps 0, 2–6 |
