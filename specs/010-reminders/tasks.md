---
type: tasks
spec_id: SPEC-009
title: reminders — Task Breakdown
description: Ordered, test-first tasks for reminders — read-only preflight (hosts, «Neon main», A and B as published, pgcrypto, no workflow C yet), the JS modules, 006_reminders.sql on the test branch and main, C and A through the MCP with pinned data, the daytime Telegram test, and exports and docs.
tags: [tasks, reminders, SPEC-009]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: null }
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

- [ ] N0 **[humano for the credential, only if it changed]**: Preflight, read-only (plan Step 0;
  RM32).
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
- [ ] N1: `recordatorios.js` (new) and the `citas.js` extension, with their tests (plan Step 1;
  RM1–RM6, RM18–RM20, RM27, RM28).
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
