---
type: tasks
spec_id: SPEC-008
title: move and cancel — Task Breakdown
description: Ordered, test-first tasks for moving and cancelling from Telegram — read-only preflight (hosts, the «Neon main» credential, the state of A and B), the JS modules, 005_move_cancel.sql on the test branch and main, A's change steps with pinned data, the Telegram test, and exports and docs.
tags: [tasks, move, cancel, SPEC-008]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# move and cancel — Tasks

Same pattern as SPEC-007. **Nothing is touched before the plan is approved.**

- One task at a time, with the human's confirmation in between.
- **[confirmación]** steps wait for the human's go-ahead before anything that creates or changes
  objects in Neon.
- **[humano]** steps need the human.
- A is only changed in M4, as a draft. The human publishes **A only**. B does not change.
- Nothing is committed unless the human asks.

- [x] M0 **[humano for the credential]**: Preflight, read-only (plan Step 0; MC32).
  - Done 2026-11-23 (17:48 UTC). Only reads were made: read-only connections to Neon, the MCP,
    and n8n's local database (metadata only). Nothing was created or changed.
  - **Neon:**

    | | `DIRECT_URL` (main) | `TEST_DATABASE_URL` |
    |---|---|---|
    | Host | `ep-steep-resonance-…` | `ep-blue-firefly-…` |
    | Branch | `br-crims…` | `br-cool-…` |
    | SPEC-004 / SPEC-007 functions | 7 of 7 / 2 of 2 | 7 of 7 / 2 of 2 |
    | `agenda_cancel*`, `agenda_move*` | 0 of 4 | 0 of 4 |
    | `cancelled_at`, `replaced_by`, `change_min_lead` | none | none |
    | Agenda configuration | 3/3/5/11/1, 0 closures | 3/3/5/11/1, 0 closures |
    | Settings | 15 min, 2 h, 30 days, limit 1, example | same |
    | Appointments | 1 `booked`, **past**: the demo limpieza of 23/11/2026 9:00–9:45 | 0 |
    | `consent` / `consent_key` | 1 `accepted` / 1 | 0 / 1 |

    The hosts differ, and both are branches of the same project. No subject or key was printed.
  - **The `Neon main` credential:** the MCP lists `QvG6Gru4fDSLvtzu`, type `postgres`. In n8n's
    local database, its `updatedAt` is **22/11/2026 16:02:39 UTC**, the SPEC-006 K5 fix,
    unchanged since. **So the human's check in the UI was not needed** (human, 2026-11-23).
  - **Workflows** (n8n 2.48.4):
    - A (35 nodes) and B (11 nodes) are active. For both, draft = published = the export in git
      (A `6a033c75…`, B `0b3cb06d…`), compared node by node and connection by connection with
      `workflow_history`.
    - A's settings are none / none / false / false, with no pinned data. B saves everything, with
      its caller policy limited to A, and `pinData: {}`.
    - **A** had one record from 17:35 UTC: the SPEC-005 transient window of a real message. It
      was gone at 17:49 UTC, and A has no saved execution.
    - **B** has 18 executions (19/11–22/11), all within their 30 days, and none after 201.
  - **Agent, read-only (nothing created or changed):**
    - the hosts of `DIRECT_URL` and `TEST_DATABASE_URL`, shortened, and their `neon.branch_id`;
    - on both branches:
      - the 7 SPEC-004 and 2 SPEC-007 functions exist;
      - `agenda_cancel*` and `agenda_move*` do not exist yet;
      - `cancelled_at`, `replaced_by` and `change_min_lead` do not exist yet;
      - the agenda configuration;
      - appointments by status and past or future, `consent` by status and `consent_key` rows,
        with no subject or key printed;
    - `Neon main`: what the MCP lists, and its `updatedAt` in n8n's local database (metadata
      only);
    - A and B active, with draft = published = the exports in git (A `6a033c75…`, B
      `0b3cb06d…`), compared with `workflow_history`;
    - A's and B's settings, no pinned data, no saved execution of A, and B's executions (count
      and dates only).
  - **Human, in the n8n UI, without saving:** open «Neon main» and check:
    - Host = `ep-steep-resonance-…`;
    - Database `neondb`, User `neondb_owner`;
    - SSL `require`, with the three certificate fields empty.

    Close it without saving, and report what was seen.
  - Check: the findings are recorded here, and nothing was created or changed.
- [x] M1: `citas.js` and `consentimiento.js` extended, with their tests (plan Step 1; MC1–MC20,
  MC27–MC29).
  - Done 2026-11-23. Nothing was touched in n8n or Neon.
  - **Red first:**
    - `citas.test.js` gained 13 SPEC-008 checks:
      - the change callbacks, their parsing and the 64-byte limit;
      - `evals/change_phrases.yaml`, with **23 positives and 22 negatives**, and a check that
        the two detectors never overlap;
      - the order with the real `urgencias.js`;
      - `plazoText`;
      - 12 `prepare` and 37 `compose` cases, with and without consent;
      - `revokedReply`;
      - the keyboard check, now 1–6 rows.

      The expected texts and buttons of 6 SPEC-007 cases changed («Cambiar» · «Anular»).
    - `consentimiento.test.js`: the SPEC-007 booking cases now expect `consent: true`, and 13
      new cases cover the three buttons allowed without consent.
    - The modules first gained only their texts and labels. Red: **13** checks of
      `citas.test.js` failed (missing functions, unknown steps, the 6 changed SPEC-007 cases), and
      **2** of `consentimiento.test.js`. `urgencias.test.js` stayed green.
  - **Green:**
    - `citas.test.js`:
      - change phrases **23/23 positives, 0/22 negatives**;
      - booking phrases still **25/25 and 0/25**;
      - 0 overlaps between the two detectors;
      - every callback ≤ 64 bytes;
      - every keyboard has 1–6 rows of one button.
    - `consentimiento.test.js` and `urgencias.test.js` are green.
    - The sync checks of `citas.js` and `consentimiento.js` are skipped «hasta M4», until A's
      export has «Componer retirada». `urgencias.js` is still checked against both exports.
  - **Choices made in the code:**
    - Without consent, the cancelled, not-active and kept replies carry only «Hablar con
      recepción». A booking keyboard needs at least one row, and the handoff button works without
      consent (SPEC-006 C12).
    - After cancelling with consent, `CANCELLED_TEXT` gets «Pedir cita» and «Hablar con
      recepción», as every booking message does (SPEC-007).
    - Change verbs are only matched in the infinitive or the imperative. «anuló» normalizes to
      «anulo», so «la clínica me anuló la cita» would otherwise match.
    - If a query does not return `change_min_lead`, the code uses its example value, 2 hours.
  - **Human review (2026-11-23):** the texts, phrases and code choices are approved. Two texts
    changed, test first (red: 3 checks, then green):
    - `MOVED_TEXT` → «Hecho: tu cita pasa al {fecha nueva} a las {hora nueva}. La anterior queda
      anulada.»;
    - the withdrawal line → «Sigues teniendo {tipo} el {fecha} a las {hora}. Si no vas a ir, puedes
      anularla aquí o llamar a recepción.»

    Both are recorded in the spec.
  - **Red first:**
    - `citas.test.js` with the change callbacks, `evals/change_phrases.yaml`, the order cases,
      the new `prepare` and `compose` cases with and without consent, `revokedReply`, the three
      changed SPEC-007 texts, and the 1–6 rows check;
    - `consentimiento.test.js` with the three buttons allowed without consent;
    - modules with only their new constants.
  - Then the functions, until green.
  - Check:
    - all three Node tests green;
    - every change positive matches and 0 negatives do;
    - the SPEC-007 booking dataset still gives 25/25 and 0/25;
    - every callback ≤ 64 bytes;
    - the sync checks are skipped until M4, as in SPEC-007 R1.
- [x] M2 **[confirmación]**: `005_move_cancel.sql` on the test branch (plan Step 2; MC21–MC23,
  MC30).
  - Done 2026-11-23, after the human saw the summarized SQL, the commands and the host
    (`ep-blue-firefly-…`, the test branch, checked by a guard before running) and confirmed.
    **Main was not touched.**
  - **`tests/infra/test_move_cancel_sql.py`**, written first: 36 tests, fake ids `900801…`, and
    dates computed from today. The key is never selected. `test_g15` of SPEC-004 now expects
    the two new columns.
  - **`app/infra/sql/005_move_cancel.sql`:**
    - `cancelled_at` and `replaced_by` on `agenda_appointments`, and `change_min_lead` (2 hours)
      on `agenda_settings`, all `ADD COLUMN IF NOT EXISTS`;
    - `agenda_cancel_at` / `agenda_cancel` and `agenda_move_at` / `agenda_move`. The move runs in
      one subtransaction: it cancels the old row, tries every professional and room, and if none
      is free a private error (`AGM01`) rolls the cancellation back.
  - **Red** (the reapply and file-exists tests excluded, so nothing was created): **35 failed**.
    There were 15 `UndefinedColumn` (`change_min_lead`, `cancelled_at`), and 14
    `UndefinedFunction` on `agenda_cancel_at` and `agenda_move_at`. The rest were the public
    functions, the two concurrency tests and `test_g15`. No fake appointment was left.
  - **Schema applied:** "Esquema aplicado en ep-blue-firefly-… (TEST_DATABASE_URL)."
  - **Green:** `test_move_cancel_sql.py` **36 passed**, including both concurrency cases and the
    double cancel. All of `tests/infra`: **170 passed**, with SPEC-002, SPEC-006, SPEC-004 and
    SPEC-007 unaffected.
  - **Afterwards** (read-only, test branch): 0 appointments, 0 closures, `consent` 0,
    `consent_key` 1, 4 new functions, and `change_min_lead` 2 hours.
  - First `tests/infra/test_move_cancel_sql.py`, then the SQL.
  - **Before running anything,** show the SQL, the exact commands and the host.
  - Run: red (nothing created), the schema, green, then all of `tests/infra`.
- [ ] M3 **[confirmación]**: `main` (plan Step 3; MC30).
  - Show the command, the host and the read-only check, and wait.
  - Run: the check before, the schema on `DIRECT_URL`, the check after.
  - **Stop if** `kb_fragments`, `consent`, `consent_key`, the agenda configuration or the
    appointments changed.
- [ ] M4: A, the change steps (plan Step 4; MC1–MC20, MC24–MC29, MC31).
  - Before changing anything, list the nodes to add, change and rewire, and wait.
  - Change the draft through the MCP, from a script that builds the code from the repo files.
  - Check the draft with a CLI export: every Code node identical to its module plus its wiring,
    the connections as planned, and the other nodes and the settings unchanged.
  - Make the pinned runs under the A4 extension (fake ids `900801…`, one run per scenario).
  - Afterwards:
    - `saveManualExecutions: false`, read back;
    - **no pinned data** in A, checked with `get_workflow_details` and a CLI export;
    - the list of executions for the human to delete.
  - Check: every scenario of plan Step 4 behaves as expected, and B is called only where
    planned.
- [ ] M5 **[humano]**: Publish **A only**, and test from Telegram (plan Step 5).
  - The agent checks `main`'s appointments (read-only, no subject), B's executions, and that A
    left no saved execution.
  - Covers: the Telegram acceptance criteria.
- [ ] M6: Exports and docs (plan Step 6; MC33).
  - Export A from its published version, without `shared` and `pinData`, and run the scan.
    Check that B's export is still its published version.
  - Run every Node and SQL test.
  - Update the README and `specs/index.md`, and mark spec, plan and tasks implemented.
