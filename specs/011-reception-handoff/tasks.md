---
type: tasks
spec_id: SPEC-010
title: reception handoff, complaints and ratings — Task Breakdown
description: Ordered, test-first tasks for the reception handoff — read-only preflight, the JS modules, 007_reception.sql on the test branch and main, the group id stored by the human, A through the MCP with pinned data, the Telegram test, and exports and docs.
tags: [tasks, reception, handoff, complaints, ratings, SPEC-010]
status: implemented
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-24T00:00:00Z }
verified: { by: human, at: 2026-11-24T00:00:00Z }
stale_after: null
---

# reception handoff, complaints and ratings — Tasks

- One task at a time, with the human's confirmation in between.
- **[confirmación]**: wait for the go-ahead before creating or changing objects in Neon or the
  workflows. Warn before anything that re-applies the schema, even on the test branch.
- **[humano]**: needs the human. Nothing is committed unless the human asks.

- [x] H0: Preflight, read-only (plan Step 0).
  - Done 2026-11-24 (about 10:40 UTC). Only reads: Neon read-only connections and n8n's local
    database (metadata only). Nothing was created or changed.
  - **Neon:** `DIRECT_URL` → `ep-steep-resonance-…` (main), `TEST_DATABASE_URL` →
    `ep-blue-firefly-…` (test); the hosts differ. On both: `pgcrypto` 1.4; 18 `agenda_*`,
    5 `consent_*` and 13 `reminder_*` functions; `agenda_reminders` and `reminder_key` present;
    **no `reception_settings`, `reception_handoffs`, `feedback_daily`, `handoff_*` or
    `feedback_*` yet**.
    - main: appointments 2 `booked` and 3 `cancelled`, 1 reminder `pending` (the SPEC-009
      test), `consent` 1, `consent_key` 1, `reminder_key` 1;
    - test: no appointments, reminders or consent rows; `consent_key` 1, `reminder_key` 1.
  - **Credentials:** `Neon main` (postgres) `updatedAt` 22/11/2026 16:02:39 UTC, unchanged since
    SPEC-006 K5, so the UI check is not needed; `Telegram LifeCenter Bot` present.
  - **Workflows:** A (`eb46a1e6…`), B (`0b3cb06d…`) and C (`9b8ccecd…`) are active, with
    draft = published = the export in git. A and C save nothing (none / none / false), B as
    before. No pinned data (A and C `null`, B `{}`).
  - **Executions:** B 21 (last 263). C had one record, 328, of its scheduled run at 10:26:56 UTC:
    the SPEC-005 transient record. Checked at 10:44 UTC: **328 is gone**. 329, of the next run at
    10:41:56, is the same case.
- [x] H1: `recepcion.js`, the `consentimiento.js` routing and the keyboard, test-first (plan
  Step 1).
  - Done 2026-11-24. Nothing was touched in n8n or Neon.
  - **Red first:** 11 checks of the new `recepcion.test.js` and 8 of `consentimiento.test.js`
    failed (17 of the 20 new `decide` cases); `citas`, `recordatorios` and `urgencias` stayed
    green. Two old expectations changed with the spec (RH1, RH2): the old `handoff` button now
    reads as a request (`reason: 'p'`), and the handoff goes through `decide` (the consent check),
    so C12's own branch is gone; a group update is the new branch that never reaches `decide`.
  - **Green:** the five Node tests. The sync checks of `recepcion.js` and `consentimiento.js` are
    skipped «hasta H4».
  - **`consentimiento.js`** (Clasificar / Decidir): `/queja`; `handoff:a|u|p|q`, `hs:<r>`, `hn`,
    `rt:u|d`; any non-private chat → a `group` route with no sender id; the strict complaint list
    (`evals/complaint_phrases.yaml`, 16 positives, 16 negatives, none of the booking or change
    phrases); `decide` for the handoff steps, `/queja`, complaint phrases and ratings, with and
    without consent, an urgency always first, and the text a handoff waits for.
  - **`recepcion.js`** (new, for «Recepción» and «Grupo de recepción»): the texts and labels,
    the reasons, the code pattern, the confirmation, the group message, the patient's texts,
    what to do with a group update (only a text reply to the bot, or «Cerrar», in the registered
    group), and the keyboard under B's replies (the reason in «Hablar con recepción», «Pedir
    cita», and 👍/👎 only under `answered`).
  - **Choice made in the code:** the complaint phrases are in `consentimiento.js` (Decidir), not
    `citas.js`, so a phrase without consent gets `COMPLAINT_NO_CONSENT_TEXT` (RH15) before the
    consent check. `citas.js` does not change: its «Hablar con recepción» buttons (`handoff`) read
    as `handoff:p`.
- [x] H2 **[confirmación]**: `007_reception.sql` on the test branch (plan Step 2).
  - Done 2026-11-24, after the human saw the summarized SQL, the commands, the host
    (`ep-blue-firefly-…`) and the warning that steps 2–4 re-apply the schema, and confirmed.
    **Main was not touched.**
  - **`tests/infra/test_reception_sql.py`**, written first (27 tests, 33 with parameters; fake
    chat ids `901001…` and a fake group `-1009010000001`, cleaned before and after; keys never
    selected): no text and no subject column; `feedback_daily` only counts; `reception_settings`
    one row and only a supergroup id; the chat id encrypted; `R-`/`Q-` codes, unique; one waiting
    handoff per patient; opening by the group message id; a failed post; the reply by message id;
    closing; 30 minutes and 48 hours; C's claim purging; withdrawal; ratings per Madrid day and
    reason; the public functions; no function returns bytes; re-applying changes nothing.
  - **`app/infra/sql/007_reception.sql`:** `reception_settings`, `reception_handoffs`,
    `feedback_daily`, the `handoff_*` and `feedback_*` functions and `reception_chat_id()`.
    **`006_reminders.sql`:** `reminder_claim_due_at` calls `handoff_purge_at` when it exists (RH20).
  - **Red** (the re-apply and file tests left out, so nothing was created): **30 failed**, each
    because a table or function did not exist yet; 0 objects created.
  - **Schema applied:** "Esquema aplicado en ep-blue-firefly-… (TEST_DATABASE_URL)."
  - **Green:** 33 passed at the first run. **`tests/infra`: 244 passed.** Afterwards the test
    branch holds 0 handoffs, settings, ratings, appointments and reminders.
  - **Limitation recorded** (human): finding a patient decrypts every stored chat id.
- [x] H3 **[confirmación]**: `main` (plan Step 3).
  - Done 2026-11-24 at 12:30 Madrid (before the SPEC-009 reminder at 16:00, so its row could not
    change between the checks), after the human saw the commands, the host
    (`ep-steep-resonance-…`, `DIRECT_URL`), the warning that step 2 re-applies the schema, and
    the read-only check, tried first on the test branch, and confirmed.
  - **Before** (read-only): `kb_fragments` 9, `consent` 1, `consent_key` 1, `reminder_key` 1;
    5 appointments, 1 reminder; 36 public functions; no reception tables or functions, and C's
    claim did not purge handoffs.
  - **Schema applied:** "Esquema aplicado en ep-steep-resonance-… (DIRECT_URL)."
  - **After**, every check «sí»: `kb_fragments`, `consent`, both keys (digests, never read), the
    whole agenda configuration, every column of the appointments and of the reminders, the trigger
    and the other 35 public functions unchanged; `reception_settings`, `reception_handoffs` and
    `feedback_daily` created and empty; the 19 new functions; `reminder_claim_due_at` changed and
    purging the handoffs. The digest file was deleted.
- [x] H3b **[humano]**: the group id into `reception_settings` with a hidden prompt (plan
  Step 3b).
  - Done 2026-11-24 by the human, at 13:22 Madrid, with the scratchpad script `h3b_grupo.py`
    (asks twice with `getpass`, checks the `-100…` form, writes, reads back in memory). Its only
    output: «guardado en reception_settings: sí | filas: 1».
  - The human set up the group: a supergroup, not in public search, auto-delete 1 week,
    restricted content, the bot as administrator. The Funnel is active again.
  - **Checked read-only by the agent, without printing the id:** 1 row, the `-100…` form (14
    characters), `reception_chat_id()` returns a value, 0 handoffs. The id is not in the repo, the
    chat, a log or n8n.
- [x] H4: A through the MCP, with pinned data (plan Step 4).
  - Done 2026-11-24 on A's draft. **Nothing was published:** A is still published at `eb46a1e6…`;
    **B (`0b3cb06d…`) and C (`9b8ccecd…`) were not touched** (C's purge is in its SQL since H3).
  - **Decision (human):** 👍 and 👎 on two rows; `answerRows` and its H1 test changed first (red,
    then green), recorded in the clarifications and RH16.
  - **Queries first on the test branch** (fake chat ids `901101–901103`, a fake group
    `-1009011000001`; everything cleaned): the consent lookup with `handoff_awaiting`, open,
    pending (with the group id from Neon, and with no row), open in the group, reply by message id
    (found, unknown, after closing), a complaint code `Q-`, a failed post, close twice, ratings
    counted, and the withdrawal with `handoff_forget`.
  - **Built through the MCP** from a script that generates the code from the repo files, in 8
    updates. A has **61 nodes**: 41 − 2 («Confirmar botón», «Responder recepción») + 22. One more
    than proposed, because «¿Hay derivación?» (no waiting row or no group id → the failure text)
    and «¿Publicado?» (Telegram's error, with `continueRegularOutput`, so it can be pinned) were
    added, and the rating reply was folded into «Recepción». A CLI export showed: the 8 Code
    nodes identical to `consentimiento.js` or `recepcion.js` plus their wiring; the queries as
    tried, each with its error output and «Neon main»; no group id in the workflow (it is read
    from Neon); the other 32 nodes, their connections and A's settings unchanged; 35 new
    connections, all to or from the new nodes.
  - **20 pinned runs** (A4 extension; fake ids `901101–901120`; «Llamar al núcleo» pinned, so B
    was never called: B still has 21 executions, the last 263), all as planned:
    - `handoff:a` with consent → the 2-row confirmation; `handoff:p` without → D8; `hs:a` →
      «Escribe…»; `hn` → «De acuerdo, no paso nada…»;
    - a waiting text → posted «[R-7KQ3] Motivo: abstención» with «Cerrar» → «Hecho… (código
      R-7KQ3)»; an urgent one → the urgency reply first and «Motivo: urgencia»; a failed post →
      `handoff_fail` → «Ahora mismo no puedo pasar tu consulta…»;
    - `/queja` with consent → the complaint confirmation (`hs:q`); without → the no-consent text;
      «quiero poner una queja por el trato recibido» → the complaint confirmation, without B;
    - a reply in the reception group → «Recepción de LifeCenter (R-7KQ3): …» to the patient; to a
      closed handoff → «Esta consulta ya está cerrada.» in the group; «Cerrar» → closed, the
      message edited with «Cerrada», the button answered; another group and a staff message
      that is not a reply → nothing sent, and no consent lookup for any group update;
    - B answered → «Pedir cita», 👍, 👎; B abstained → «Hablar con recepción» `handoff:a`, no
      rating; 👍 with consent → counted, the buttons removed, «Gracias por tu valoración.»; 👎
      without → the notice; the withdrawal → `Cita tras retirar` with `handoff_forget`.
  - **Afterwards:** `saveManualExecutions: false`, read back; no pinned data in A (`null`), B
    (`{}`) or C (`null`); B and C equal to their git exports; nothing published.
  - **Executions for the human to delete** (2026-11-24, 12:47:43–12:51:59 UTC): **A (20):**
    342–361. There are no others after 341 (341 is C's transient record).
- [x] H5 **[humano]**: the auto-delete timer (1 week), publish A, Telegram test (plan Step 5).
  - Closed 2026-11-24 by the human, with `/queja` and the ratings still pending in real.
  - The human set the group's auto-delete to 1 week (H3b) and published **A only** (`ba5413f3…`);
    B and C were not republished.
  - **From Telegram:** «cuánto cuesta una limpieza» got D7, because **Gemini answered 503 (high
    demand)**: B 365 and 376 returned `llm_error`, receiving only `question`. A was fine. From that
    D7, «Hablar con recepción» (`handoff:p`) → the confirmation → the message → «Hecho… R-U4RK» →
    in the group «[R-U4RK] Motivo: petición» with «Cerrar» → a reply in the group → the patient got
    «Recepción de LifeCenter (R-U4RK): solo por las mañanas, de 10 a 14.» → «Cerrar». A group
    message that was not a reply was ignored.
  - **Checked read-only on `main`** (no chat id or group id printed): R-U4RK no longer exists
    (closed and deleted), 0 handoffs, ratings 0/0, the group stored. A's executions 364, 367,
    369–375 and C's 366 are the SPEC-005 transient records.
  - With pinned data in H4: the 17 scenarios (20 runs).
  - **Rest of the real test, 2026-11-24 (evening), by the human**, after B's Gemini node got one
    retry (SPEC-001 Q12, changed that day) and answered again:
    - `/queja` → Q-RHWR posted in the group, the reply reached the patient, closed;
    - 👍 on an answered reply; an urgency passed to reception (R-NUJ5) and its reply after
      closing;
    - **checked read-only on `main`** (no chat id or group id printed): B 384 `answered` and 394
      `urgency`, both receiving only `question`; `feedback_daily` 24/11 `answered` 1 up, 0 down.
      Q-RHWR and R-NUJ5 were still open at the first check, because «Cerrar» had not been tapped
      on them; the human tapped it (A's records 398–399, «Cerrar» in the group, 18:34 UTC) and
      **both were deleted**: 0 handoffs left.
  - A consent notice in the group from 13:18, before the new A was published, was not tapped.
    **Nothing is pending.**
- [x] H6: Exports and docs (plan Step 6).
  - Done 2026-11-24. A exported from its published version (`ba5413f3…`, equal to n8n's
    `workflow_history`), without `shared` and `pinData`; B and C byte for byte equal to git.
  - Every Node test is green, and every sync check runs (no skip left). `pytest`: **413 passed**,
    with the 12 tests that re-apply the schema left out (human rule of 2026-11-24).
  - Scan of the diff and of the pending commits: no full Neon host, no real group id, no real chat
    id (checked against `main` in memory).
  - README (A, the reception section, Try it, the export and the tests), `specs/index.md`, and
    spec, plan and tasks implemented.
