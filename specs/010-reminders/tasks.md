---
type: tasks
spec_id: SPEC-009
title: reminders — Task Breakdown
description: Ordered, test-first tasks for reminders — read-only preflight (hosts, «Neon main», A and B as published, pgcrypto, no workflow C yet), the JS modules, 006_reminders.sql on the test branch and main, C and A through the MCP with pinned data, the daytime Telegram test, and exports and docs.
tags: [tasks, reminders, SPEC-009]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# reminders — Tasks

Same pattern as SPEC-008. **Nothing is touched before the plan is approved.**

- One task at a time, with the human's confirmation in between.
- **[confirmación]** steps wait for the human's go-ahead before anything that creates or changes
  objects in Neon.
- **[humano]** steps need the human.
- A and C are only changed in N4, as drafts. The human publishes **C, then A**. B does not change.
- Nothing is committed unless the human asks.

- [x] N0 **[humano for the credential, only if it changed]**: Preflight, read-only (plan Step 0;
  RM32).
  - Done 2026-11-23 (20:14 UTC). Only reads were made: read-only connections to Neon, the MCP, and
    n8n's local database (metadata only). Nothing was created or changed.
  - **Neon:**

    | | `DIRECT_URL` (main) | `TEST_DATABASE_URL` |
    |---|---|---|
    | Host | `ep-steep-resonance-…` | `ep-blue-firefly-…` |
    | Branch | `br-crims…` | `br-cool-…` |
    | `pgcrypto` | 1.4 | 1.4 |
    | SPEC-004/007/008 functions | 13 of 13 | 13 of 13 |
    | SPEC-009 tables, `reminder_*` functions, `attendance_confirmed_at`, the 3 settings, the trigger | none | none |
    | Appointments | 1 `booked` (the demo one, past), 3 `cancelled` (the SPEC-008 test) | 0 |
    | `consent` / `consent_key` | 1 `accepted` / 1 | 0 / 1 |

    The hosts differ, and both are branches of the same project. No subject or key was printed.
  - **Credentials:**
    - `Neon main` (`QvG6Gru4fDSLvtzu`, postgres): `updatedAt` **22/11/2026 16:02:39 UTC**, unchanged
      since SPEC-006 K5. **The human's UI check is not needed.**
    - `Telegram LifeCenter Bot` (`VzY1vvAFNqi3JSKT`) is present; C will use it.
  - **Workflows:**
    - A (40 nodes) and B (11 nodes) are active. For both, draft = published = the export in git
      (A `7c3d4100…`, B `0b3cb06d…`).
    - A's settings are none / none / false / false, with no pinned data and no saved execution.
      B's settings are as before (saves everything, caller policy limited to A), with
      `pinData: {}` and 21 executions, the last on 23/11 19:36 UTC.
    - **No workflow C yet:** `search_workflows` finds nothing for «reminder» or «recordatorio»,
      and n8n's local database has none.
  - **Agent, read-only (nothing created or changed):**
    - the hosts of `DIRECT_URL` and `TEST_DATABASE_URL`, shortened, and their branch ids;
    - on both branches:
      - `pgcrypto` installed;
      - the SPEC-004, SPEC-007 and SPEC-008 functions present;
      - none of the SPEC-009 tables, columns, settings or functions yet;
      - appointments by status, `consent` by status and `consent_key` rows, with no subject or
        key printed;
    - `Neon main`: what the MCP lists, and its `updatedAt` (metadata only). If it changed since
      22/11/2026 16:02 UTC, the human checks it in the UI;
    - A and B active, with draft = published = the export in git (A `7c3d4100…`, B `0b3cb06d…`);
      their settings; no pinned data; no saved execution of A;
    - **no workflow C yet**: no `lifecenter-reminders` in the MCP's `search_workflows` or in n8n's
      local database;
    - the Telegram credential `VzY1vvAFNqi3JSKT` present.
  - Check: the findings are recorded here, and nothing was created or changed.
- [x] N1: `recordatorios.js` (new) and the `citas.js` extension, with their tests (plan Step 1;
  RM1–RM6, RM18–RM20, RM27, RM28).
  - Done 2026-11-23. Nothing was touched in n8n or Neon.
  - **Red first:**
    - `recordatorios.test.js` (new): texts, `CLINIC_ADDRESS` marked as example, `whenText` (tomorrow,
      today, later, both DST changes, a new year), `composeReminder` (no type, 4 buttons, 64
      bytes), `classifySendError`, and the sync check with C;
    - `citas.test.js`: `bk:ry`, `bk:rn`, `bk:rq` and `bk:i`; 4 `prepare` and 16 `compose` cases;
      consent required; the withdrawal line. The expected «booked» case of SPEC-007 gains the
      offer;
    - `consentimiento.test.js`: 7 cases, the reminder buttons with and without consent.
    - With only the new texts and labels in the modules: **5** checks of `recordatorios.test.js`
      and **7** of `citas.test.js` failed. `consentimiento.test.js` was already green.
      `urgencias.test.js` stayed green.
  - **Green:** the four Node tests are green.
    - The sync checks of `citas.js` (A) and `recordatorios.js` (C) are skipped «hasta N4».
      `consentimiento.js` and `urgencias.js` are still checked against the exports.
    - SPEC-007's 25/25 and 0/25 and SPEC-008's 23/23 and 0/22 are unchanged.
  - **Choices made in the code:**
    - **`consentimiento.js` does not change:** the reminder buttons are `bk:` buttons, which need
      consent by default, as the 7 new cases show.
    - The view shows the reminder line and button only when the query says whether there is a
      reminder (`has_reminder` true or false) and the appointment is at least 3 hours away.
      Otherwise it is the SPEC-008 view.
    - «Iré» answers with `ATTENDANCE_TEXT` and the «Cambiar» · «Anular» · «Hablar con recepción»
      buttons.
    - `recordatorios.js` has its own Madrid date helpers, so C carries a single module.
    - `CLINIC_ADDRESS` is «Calle de Ejemplo 1, Madrid», with `CLINIC_ADDRESS_IS_EXAMPLE = true`.
  - **Red first:** `recordatorios.test.js` and the new `citas.test.js` cases, with modules that only
    gain their texts.
  - Then the functions, until green. `consentimiento.test.js` and `urgencias.test.js` stay green.
  - The sync checks of `citas.js` and `recordatorios.js` are skipped «hasta N4».
- [ ] N2 **[confirmación]**: `006_reminders.sql` on the test branch (plan Step 2; RM7–RM17, RM19,
  RM24–RM26, RM29).
  - First `tests/infra/test_reminders_sql.py`, then the SQL.
  - **Before running anything,** show the SQL, the exact commands and the host.
  - Run: red (nothing created), the schema, green, then all of `tests/infra`.
- [ ] N3 **[confirmación]**: `main` (plan Step 3; RM29).
  - Show the command, the host and the read-only check, and wait.
  - Run: the check before, the schema on `DIRECT_URL`, the check after.
  - **Stop if** `kb_fragments`, `consent`, `consent_key`, the agenda configuration or the
    appointments changed.
- [ ] N4: C (new) and A, with pinned data (plan Step 4; RM1–RM23, RM30).
  - Before changing anything, list the nodes to add, change and rewire, and wait.
  - Try the new queries on the test branch first, with fake ids and cleanup.
  - Build C with the Workflow SDK and change A, both through the MCP, from scripts that build the
    code from the repo files. Check both with a CLI export.
  - Make the pinned runs under the A4 extension (ids `900951…`, one run per scenario).
  - Afterwards:
    - `saveManualExecutions: false` in A and C, read back;
    - no pinned data in A, B or C;
    - B intact;
    - the exact list of executions for the human to delete.
- [ ] N5 **[humano]**: Publish **C, then A**, and test from Telegram (plan Step 5; RM31).
  - In daytime (outside 21:00–9:00 Madrid), with n8n running, on an appointment booked more than
    3 hours ahead.
  - The agent checks, read-only with no subject or chat id printed, the reminder rows,
    `attendance_confirmed_at`, and that A and C saved no executions and B received only
    `question`.
- [ ] N6: Exports and docs (plan Step 6; RM33).
  - Export A and C from their published versions, without `shared` and `pinData`. C is a new
    file. Check that B's export is still its published version.
  - Run the scan (including both full Neon hosts), every Node test and `pytest`.
  - Update the README and `specs/index.md`, and mark spec, plan and tasks implemented.
