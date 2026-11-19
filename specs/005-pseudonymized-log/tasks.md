---
type: tasks
spec_id: SPEC-005
title: pseudonymized-log — Task Breakdown
description: Ordered tasks to check the retention, build the core workflow B, slim the channel workflow A, publish and test, set 30-day pruning, delete the old history, run the short pruning test and export and document.
tags: [tasks, pseudonymized-log, SPEC-005]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# pseudonymized-log — Tasks

Same order as SPEC-003: first B with pinned data, then A, then the human publishes and tests from
Telegram. One task at a time, with the human's confirmation in between. The workflows are not
touched before the plan is approved. Steps marked **[humano]** need the human. Nothing is
committed unless the human asks.

- [x] L0: Check the current retention (read-only, plan Step 0).
  - Done 2026-11-19. Nothing was changed.
  - **No `EXECUTIONS_*` variable is set anywhere:** not in the n8n process, nor in the User or
    Machine environment, nor in `.env` (only `N8N_BASE_URL`, `N8N_MCP_TOKEN` and
    `N8N_WEBHOOK_URL`). `~/.n8n/config` only holds `encryptionKey`. `n8n-start.ps1` only sets
    `WEBHOOK_URL` and `N8N_EDITOR_BASE_URL`.
  - **The effective values are the n8n 2.48.4 defaults**, read from
    `@n8n/config/dist/configs/executions.config.js`:

    | Setting | Variable | Default |
    |---|---|---|
    | Pruning | `EXECUTIONS_DATA_PRUNE` | `true` |
    | Maximum age | `EXECUTIONS_DATA_MAX_AGE` | **336 h (14 days)** |
    | Maximum count | `EXECUTIONS_DATA_PRUNE_MAX_COUNT` | 10 000 |
    | Hard-delete buffer | `EXECUTIONS_DATA_HARD_DELETE_BUFFER` | 1 h |
    | Soft-delete interval | `EXECUTIONS_DATA_PRUNE_SOFT_DELETE_INTERVAL` | 60 min |
    | Hard-delete interval | `EXECUTIONS_DATA_PRUNE_HARD_DELETE_INTERVAL` | 15 min |

    The instance's default saving is `saveDataOnSuccess` and `saveDataOnError` set to `all`.
  - **Conclusion:** the instance **already prunes, at 14 days**. CHG-001 D11's "no se borran
    nunca" was not accurate. SPEC-005 sets 30 days explicitly (P10), which **extends** retention
    from 14 to 30 days, as NFR-08 asks.
  - **Pruning timing:** an execution older than the maximum age is soft-deleted within at most
    60 min, and hard-deleted after the 1 h buffer, at the next 15-min pass. This sets the waits for
    the L6 short test.
  - **Oldest execution** visible through the MCP: 20 (manual, 2026-11-18 18:29 UTC) of
    `lifecenter-telegram-demo`. Executions of workflows that are not available in MCP are not
    listed.
  - **n8n event logs** (`~/.n8n/n8nEventLog*.log`): they hold audit and workflow events. A count
    of test strings ("sangra", "612 345 678", "Ana Garc", the test username, `question`,
    `first_name`) found 0 occurrences, so message content is not logged there.
  - Find the effective `EXECUTIONS_DATA_*` values: the environment, `.env` (names only),
    `~/.n8n/config` and the defaults of the installed n8n. Also find the oldest stored execution.
  - Check: the values are recorded here, and nothing has been changed.
  - Covers: P10 (baseline), P11.
- [x] L1: Core workflow B, `lifecenter-demo-core` (plan Step 1).
  - Done 2026-11-19. B id: `v7Bxk8HuE4GQ3lBl`; unpublished.
  - **Built from A's current export:** a script generated B's workflow JSON and `n8n
    import:workflow` imported it, instead of pasting about 21 KB of code through the MCP. This
    deviates from the plan's "through the MCP": the node contents are generated, not hand-copied.
  - **Checked on a temporary export:**
    - all 11 nodes have exactly the generated parameters (0 differences);
    - the credentials are set by id (`Neon main`, `Gemini API`), and "Gemini" keeps its error
      output;
    - the settings are as planned (save all; caller policy limited to A,
      `q3f5dVrl8OUsXJrG`; available in MCP);
    - "Detectar urgencia" starts with `urgencias.js`;
    - no node references `chatId` or "Seudonimizar".
  - **Pinned run (execution 72 of B)**, 5 questions:

    | Question | Path and result |
    |---|---|
    | "me sangra mucho la encia desde ayer" | `urgent` → "Resultado" |
    | "se me ha hinchado la cara y me cuesta tragar" | `severe` → "Resultado" |
    | "Me llamo [NOMBRE], ¿cuanto cuesta una limpieza?" | Neon, Gemini, validation: `answered`, 60 € with both notices |
    | "¿aceptais el seguro de sanitas?" | `below_threshold` |
    | "¿cuanto dura una ortodoncia?" | `model_abstained` |

    - "Preparar prompt" takes each question from "Recibir pregunta" with the right pairing.
    - "Resultado" returns only whitelisted fields. No output contains `chatId` or any Telegram
      field.
  - **Not covered by the pinned run:** the Gemini **error** path. `test_workflow` always pins HTTP
    Request nodes, so it cannot produce an error output. The path is checked structurally ("Gemini"
    error output → "Error" → "Resultado", in the export), and it ran for real before the split
    (executions 37, 42, 43).
  - **Note for L2:** A calls B **once per item**, so each call follows a single path and "Resultado"
    runs once per call. This is what A receives.
  - Create B through the MCP: the "Recibir pregunta" trigger with the `question` field, the nine
    nodes without the chat id, the "Resultado" whitelist, and the save and caller settings.
  - Check: a pinned run with urgent, severe, answered, below-threshold and model-abstained items,
    plus a Gemini error. Each takes the right path, "Resultado" returns only the whitelisted
    fields, and no node output contains `chatId` or any Telegram field. The code of "Detectar
    urgencia" starts with `urgencias.js`.
  - Covers: P2, P5–P7.
- [x] L2: Channel workflow A (plan Step 2).
  - Done 2026-11-19, unpublished. The published version of A is still the SPEC-003 one until L4.
  - **Changes, through the MCP:**
    - removed the 9 nodes now in B;
    - added "Llamar al núcleo": B by id `v7Bxk8HuE4GQ3lBl`, once per item, wait for
      completion, input `question = {{ $json.question }}` only;
    - added "Componer respuesta": B's fields plus `chatId` from "Seudonimizar";
    - wiring "Seudonimizar → Llamar al núcleo → Componer respuesta → ¿Ofrecer recepción?";
    - updated the description. A now has 11 nodes.
  - **Synthetic pinned run (execution 73 of A, the approved exception A4)**, with fake chat ids
    900001–900004:
    - the name and phone message → B → 280 € with TAR-001 and both notices, replied to chat 900001;
    - "me sangra mucho la encia desde ayer" → B → `urgent`, with the button, to chat 900002;
    - the sticker → "Pedir texto" (D12);
    - the button → "Confirmar botón" → "Responder recepción" (D8).
  - **Two B executions created by that run (74, 75; mode `integrated`):** they contain only
    `question`, already pseudonymized ("Me llamo [NOMBRE] y mi móvil es [TELEFONO]…"), and the
    reply fields. No chat id, user id or profile name appears; only a reference to A's
    execution 73. B was **not published**, and the manual run called it anyway.
  - **Settings:** `saveManualExecutions` went back to `false` right after the run. Read back
    through the MCP, the final settings are `saveDataSuccessExecution: none`,
    `saveDataErrorExecution: none`, `saveManualExecutions: false` and
    `saveExecutionProgress: false`.
  - **Reminder for L5:** execution 73 of A (synthetic) and executions 72–75 of B are deleted with
    the old history.
  - Remove the nine moved nodes. Add "Llamar al núcleo" (once per item; input `question` only)
    and "Componer respuesta". Set the no-save settings, with `saveManualExecutions` on for **one**
    synthetic pinned run and then off.
  - Check: the pinned run (text → B → reply to the right chat id; button → D8; sticker → D12); B's
    execution from that run has no identifier; A's settings end as none, none, false, false.
  - Covers: P1, P3, P4, P8.
- [x] L3: Retention in `n8n-start.ps1` (plan Step 3).
  - Done 2026-11-19.
  - **Parameter:** `-ExecutionsMaxAgeHours` (`[int]`, default 720, `ValidateRange(1, 87600)`).
  - **Process variables:** the script sets `EXECUTIONS_DATA_PRUNE=true` and
    `EXECUTIONS_DATA_MAX_AGE=<n>` for its own process only. The other pruning variables are not
    set.
  - **Messages on start:** it prints "Retención de ejecuciones: EXECUTIONS_DATA_PRUNE=true
    EXECUTIONS_DATA_MAX_AGE=<n> (horas)". With any value other than 720 it shows a yellow warning
    to restart with `.\n8n-start.ps1` after the test.
  - **Checks:**
    - the PowerShell parser reports 0 errors;
    - the UTF-8 BOM is kept;
    - the parsed default is 720;
    - 0 and -5 are rejected by the validation before anything runs.

    A valid value was not run, because it would start n8n. That happens in L4.
  - Add the `-ExecutionsMaxAgeHours` parameter (default 720), set `EXECUTIONS_DATA_PRUNE=true`
    and `EXECUTIONS_DATA_MAX_AGE`, and print both values.
  - Check: the PowerShell parser reports 0 errors and the BOM is kept.
  - Covers: P10, P12 (mechanism).
- [x] L4 **[humano]**: Restart, publish and test from Telegram (plan Step 4).
  - **Closed 2026-11-19 after a re-send** (20:46–20:48 local time). Four new B executions:
    - 88 (from A 87), the injection → `model_abstained`;
    - 90 (from A 89), the severe message → `severe` (112);
    - 92 (from A 91), "¿la limpieza duele?" → `none`, then `model_abstained`;
    - 95 (from A 94), "Una pegatina" written as text → `below_threshold`.

    The button (D8) and a photo (D12) replied correctly in Telegram and, as designed, produced no
    B execution.
  - **Scan:** none of the 9 B executions (77–85, 88–95) contains a chat id, Telegram profile
    name, username, "Ana García" or "612 345 678". A still has **0** stored executions.
  - **Unexplained:** the first attempt at those three messages (around 20:42–20:45) left no B
    execution. A stores nothing, failures included, so n8n has no trace of the cause; the re-send
    worked. This is the accepted cost of Q4. If it happens again, the n8n console is the only
    source.
  - **In progress, 2026-11-19.** The human restarted n8n (PRUNE=true, MAX_AGE=720), published B
    and then A, and sent the test messages from 20:41 local time.
  - **What the agent found:**
    - **A:** 0 stored executions, as P8 and P9 require. Its executions 76, 78, 80, 82 and 84 exist
      only as `parentExecution` references from B.
    - **B:** 5 executions:
      - 77, limpieza → 60 €;
      - 79, sábados → HOR-001;
      - 81, Sanitas → `below_threshold`;
      - 83, name and phone → `[NOMBRE]`/`[TELEFONO]`, 280 €;
      - 85, gum bleeding → `urgent`.
    - **Scan of those 5:** no chat id, Telegram profile name or username, "Ana García" or
      "612 345 678".
  - **Open:** there is no B execution for the injection, the severe message or "¿la limpieza
    duele?", and none at all after 20:42:54 local time. Because A stores nothing, failures
    included, n8n leaves no trace. Pending: the human's report of the Telegram replies and of the
    n8n console, or a re-send.
  - Restart n8n with `.\n8n-start.ps1`; it must print PRUNE=true and MAX_AGE=720.
  - Publish **B, then A**, and send the acceptance messages and the button. The agent checks the
    Executions list and scans the new B executions.
  - Covers: acceptance criteria 1–4.
- [ ] L5 **[humano]**: Delete the old history (plan Step 5).
  - **Reminder:** once L4 passes, delete from the n8n editor every execution from before the
    switch. They contain raw messages, your Telegram profile name and username, and test phones.
    This includes all old executions of A and the synthetic one of L2.
  - The agent then checks that none older than the switch remains.
  - Covers: P13; acceptance criterion 8.
- [ ] L6 **[humano, asks for confirmation before restarting]**: Short pruning test (plan Step 6).
  - Preconditions: L5 done, and at least one execution of B more than 1 hour old.
  - The agent asks for confirmation and warns that the test deletes **every** execution older than
    1 hour on the whole instance.
  - Start with `.\n8n-start.ps1 -ExecutionsMaxAgeHours 1`, check that the old B executions are
    deleted and the recent ones remain, then restart with `.\n8n-start.ps1` (720).
  - Covers: P11, P12; acceptance criterion 5.
- [ ] L7: Exports and docs (plan Step 7).
  - Export A and B with the `shared` block removed, and run the scan.
  - Point the sync check of `urgencias.test.js` at B's export; the test must be green.
  - Update the README "Demo" section and `specs/index.md`.
  - Covers: P14–P16; acceptance criteria 6–7.
