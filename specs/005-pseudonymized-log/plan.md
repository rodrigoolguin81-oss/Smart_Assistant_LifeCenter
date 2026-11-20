---
type: plan
spec_id: SPEC-005
title: pseudonymized-log — Technical Plan
description: How to check the current retention, build the core workflow lifecenter-demo-core, slim the channel workflow down to receive, pseudonymize and reply with no stored executions, set 30-day pruning in n8n-start.ps1, run the one-off short pruning test, and export and document both workflows.
tags: [plan, pseudonymized-log, SPEC-005, n8n]
status: implemented
sources: [./spec.md, ./clarifications.md, ../003-n8n-migration/plan.md, ../004-urgencies/plan.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# pseudonymized-log — Plan

## Architecture

```text
A  lifecenter-telegram-demo   (saves NO executions)
   Telegram Trigger → ¿Qué ha llegado?
     ├─ Botón → Confirmar botón → Responder recepción (D8)
     ├─ Otro  → Pedir texto (D12)
     └─ Texto → Seudonimizar → Llamar al núcleo ──(question only)──▶ B
                               ◀── reply fields (no identifier) ──┘
              → Componer respuesta (adds A's own chatId) → ¿Ofrecer recepción?
                → Responder con botón | Responder

B  lifecenter-demo-core       (saves executions; the demo shows each path here)
   Recibir pregunta {question}
     → Detectar urgencia → ¿Es urgencia?
          ├─ yes ───────────────────────────────────────────────────────┐
          └─ no  → Buscar en kb → ¿Hay contexto?                         │
                     ├─ no  → Abstención ────────────────────────────────┤
                     └─ yes → Preparar prompt → Gemini ─┬─ ok    → Validar y componer ┤
                                                         └─ error → Error ────────────┤
                                                                                       ▼
                                                                                  Resultado
```

## Step 0: Current retention, checked before changing it (read-only)

The goal is to learn what this instance does today. Nothing is changed in this step.

1. Look for `EXECUTIONS_DATA_*` and `EXECUTIONS_*` variables in three places:
   - the environment of the user and of the machine (Windows `User` and `Machine` scopes);
   - `.env`, by variable name only, without printing values;
   - `~/.n8n/config`, if it exists.
2. Read the defaults of the installed n8n version (2.48.4) from its own package, by searching
   the n8n package under the global `node_modules` for the pruning settings: prune on/off, maximum
   age, maximum count and the hard-delete buffer.
3. Find the oldest stored execution through the MCP.
4. Report the effective values and record them in the tasks. If pruning is already on at 14 days,
   then the change in Step 3 extends retention to 30 days. That is still what NFR-08 asks.

## Step 1: Core workflow B, `lifecenter-demo-core` (new, created through the MCP)

- **Trigger.** "Recibir pregunta" is an Execute Workflow Trigger whose input is defined by
  fields, with one field: `question` (string). B accepts nothing else (P5).
- **Nodes.** The nine logic nodes are copied from A with the same parameters and credentials:
  `Neon main` and `Gemini API` by id; model `gemini-flash-lite-latest`; timeout 20 000 ms. They
  change only where they read the chat id or "Seudonimizar":
  - **Detectar urgencia:** `urgencias.js` stays byte for byte. The wiring drops `chatId`, so an
    urgency returns `{ text, handoff, reason, urgency_level, matched }` and `none` returns
    `{ question, urgency_level }`.
  - **Preparar prompt:** the question is read from `$('Recibir pregunta').item.json.question`.
    It no longer outputs `chatId`.
  - **Abstención, Error and Validar y componer:** `chatId` is removed from their output.
- **"Resultado".** A Code node where the four ends (urgency, abstention, error, validation)
  converge. It returns **only** this whitelist of fields (P6):
  - `text`, `handoff`, `reason`;
  - `urgency_level`, `matched`, `failure`, `error_kind`, `citations`, `top_score`;
  - `model_answer`, `usage`.

  Anything else is dropped, so no identifier can leak back by accident, and B always ends in one
  node, whose output is what A receives.
- **Settings:**
  - save successful, failed and manual executions (B is where the demo looks);
  - execution order v1;
  - `callerPolicy: workflowsFromAList`, with A's id only, so no other workflow can call it.
- **Publishing.** In n8n 2.x a sub-workflow call may use B's published version. The pinned test
  of Step 1 shows which version runs. B is published by the human in Step 4, before A.

**Test with pinned data** (MCP `test_workflow`; B's trigger is pinned with `{ question }`, and
Postgres and Gemini are pinned): five items, one per path:

- urgent;
- severe;
- answered (60 € with TAR-001);
- below threshold;
- model abstained.

Check, for each one: the path taken, `Resultado`'s fields, and that **no** node output contains
`chatId` or any Telegram field. Then a forced Gemini error (pinned error output, or a manual test
with a wrong model name if pinning cannot produce it) → the D7 text from "Error" → "Resultado".

## Step 2: Channel workflow A, `lifecenter-telegram-demo` (changed through the MCP)

- **Remove** the nine nodes moved to B.
- **Add "Llamar al núcleo"**, an Execute Workflow node:
  - source: database, workflow B by id;
  - mode: **run once for each item**, so each message maps 1:1 to its result and pairing is
    kept;
  - wait for completion;
  - inputs: only `question = {{ $json.question }}`.
- **Add "Componer respuesta"**, a Code node per item. It returns
  `{ ...$json, chatId: $('Seudonimizar').item.json.chatId }`: B's reply fields plus A's own chat
  id. Then come "¿Ofrecer recepción?", "Responder con botón" and "Responder", unchanged.
- **Unchanged:** "¿Qué ha llegado?", "Seudonimizar", "Pedir texto", "Confirmar botón" and
  "Responder recepción".
- **Settings (P8):**
  - `saveDataSuccessExecution: none`;
  - `saveDataErrorExecution: none`;
  - `saveManualExecutions: false`;
  - `saveExecutionProgress: false`.
- **Test with pinned data.** Because A saves no manual executions, a pinned run of A cannot be
  inspected afterwards. Plan decision, to approve:
  1. Make the Step 2 changes with `saveManualExecutions: true` for **one** pinned run with
     **synthetic** data only.
  2. Check that run: text → B → reply with the right chat id; button → D8; sticker → D12.
  3. Set `saveManualExecutions: false` immediately, before anything is published.

  The run's synthetic data contains no personal data, and that execution is deleted with the old
  history in Step 5. A's pinned run calls B's version as configured, and that call is itself
  saved as an execution of B. That B execution is checked for absent identifiers.

## Step 3: Retention in `n8n-start.ps1`

- Add `param([int]$ExecutionsMaxAgeHours = 720)`.
- The script sets `$env:EXECUTIONS_DATA_PRUNE = 'true'` and
  `$env:EXECUTIONS_DATA_MAX_AGE = $ExecutionsMaxAgeHours`, for that process only, like
  `WEBHOOK_URL`. The other pruning variables are not set, so they keep the defaults recorded in
  Step 0.
- It prints `EXECUTIONS_DATA_PRUNE=true` and `EXECUTIONS_DATA_MAX_AGE=<n>` on start (P10).
- It rejects a value below 1.
- `.\n8n-start.ps1` gives 720. `.\n8n-start.ps1 -ExecutionsMaxAgeHours 1` gives the short test,
  with no file edited (P12).
- Check: the PowerShell parser reports 0 errors, the UTF-8 BOM is kept, and the human restarts n8n
  normally.

## Step 4: Publish and test from Telegram [human]

Publish **B first**, then **A**. Send the acceptance messages:

- the CHG-001 messages: limpieza, sábados, Sanitas, name and phone, the injection and a sticker;
- the SPEC-003 messages: urgent, severe and a non-urgent one;
- the button.

The agent then:

- lists executions through the MCP: no new entry for A, and one entry for B per text message;
- scans every new B execution for the test chat id, the Telegram profile name and username, "Ana
  García" and "612 345 678". None may appear.

## Step 5: Delete the old history [human, reminder]

Once Step 4 passes, the human deletes from the editor every execution from before the switch,
including all old executions of A and the synthetic one of Step 2. The agent then checks through
the MCP that no execution older than the switch remains.

## Step 6: One-off short pruning test [human, asks for confirmation before restarting]

Preconditions:

- Step 5 is done;
- at least one execution of B is more than 1 hour old;
- the human has been warned that, while it runs, the test deletes **every execution older than
  1 hour on the whole instance**, including other workflows.

Procedure:

1. The agent asks for confirmation.
2. The human stops n8n and starts it with `.\n8n-start.ps1 -ExecutionsMaxAgeHours 1`.
3. The agent records the B executions older than 1 hour before, and checks through the MCP after
   n8n's pruning cycle (soft delete, then hard delete after the buffer found in Step 0) that they
   are gone and that the recent ones remain.
4. The human restarts with `.\n8n-start.ps1`, which gives 720 again. The agent records the result.

## Step 7: Exports and docs

- Export **A** to `n8n/workflows/lifecenter-telegram-demo.json` and **B** to
  `n8n/workflows/lifecenter-demo-core.json`, with the `shared` block removed, then run the secret
  and personal-data scan (CHG-001 procedure). A's export must carry its no-save settings (P14).
- In `n8n/code/urgencias.test.js`, point the sync check at B's export (P15). The test stays green.
- README "Demo":
  - the two-workflow diagram;
  - "the path of each message is in the executions of `lifecenter-demo-core`";
  - the 30-day deletion and the short-test option;
  - import B before A and select its credentials;
  - the SPEC-005 limitations (P16).
- `specs/index.md`. CHG-001's D11 note is already written (P17).

## Requirement → component map

| Requirement | Component |
|---|---|
| P1–P4 | A's nodes and wiring (Step 2) |
| P5, P6 | B's trigger field, "Llamar al núcleo" inputs, "Resultado" whitelist |
| P7 | B's node changes (no chat id); scan in Step 4 |
| P8, P9 | A's settings; executions check in Step 4 |
| P10 | `n8n-start.ps1` (Step 3) |
| P11, P12 | n8n pruning; short test (Step 6) |
| P13 | Step 5 |
| P14–P16 | Step 7 |
| P17 | CHG-001 clarifications (already written) |
