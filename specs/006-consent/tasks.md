---
type: tasks
spec_id: SPEC-006
title: consent — Task Breakdown
description: Ordered, test-first tasks to build the consent step of the n8n demo — facts, consent module and Node test, Neon schema on the test branch and on main, changes to A with pinned data, Telegram test, and exports and docs.
tags: [tasks, consent, SPEC-006]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-21T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# consent — Tasks

Same order as SPEC-003 and SPEC-005:

1. The module and its Node test, test first.
2. Neon, only after the human confirms.
3. A, with pinned data.
4. The human publishes and tests from Telegram.

One task at a time, with the human's confirmation in between. **The workflows are not touched
before the plan is approved.** Steps marked **[humano]** need the human, and steps marked
**[confirmación]** wait for the human's go-ahead before creating anything. Nothing is committed
unless the human asks.

- [ ] K0: Facts, read-only (plan Step 0).
  - Check that `pgcrypto` is available and installed on the test branch and on main.
  - Read the role names in `DIRECT_URL` and `TEST_DATABASE_URL` from `.env`, without printing
    the password or the full URL. `Neon main` was created from the parts of `DIRECT_URL`
    (human, 2026-11-22), so it uses the same role.
  - Check in the n8n node types: expressions in the Telegram node's `callback_data`, and
    `isExecuted` in Code nodes.
  - Check: the findings are recorded here, and nothing was created or changed.
  - Covers: preconditions of C18, C19 and Step 4.
- [ ] K1: `consentimiento.js` and its Node test (plan Step 1).
  - First `n8n/code/consentimiento.test.js`: the texts, the decision table, the 64-byte limit,
    commands, version, dates and the sync check. It must be **red** for the right reason: only
    the missing functions fail.
  - Then `n8n/code/consentimiento.js`, until the test is green.
  - Point the sync check of `urgencias.test.js` at both exports. It stays green; A's check is
    skipped for now.
  - Check: both tests green; A's sync checks reported as skipped.
  - Covers: C1–C16 (logic), C22–C25.
- [ ] K2 **[confirmación]**: Neon schema on the test branch (plan Step 2).
  - First `tests/infra/test_consent_sql.py` (red: no functions yet).
  - Then `app/infra/sql/002_consent.sql` and the `__main__` of `app/infra/schema.py`.
  - **Before running anything against the test branch, the agent asks for confirmation:** it
    creates `pgcrypto`, `consent_key` with its key, `consent` and the functions.
  - Check: the test is green on `TEST_DATABASE_URL`, and the key is never printed.
  - Covers: C17–C20.
- [ ] K3 **[confirmación]**: Neon schema on main (plan Step 3).
  - **The agent asks for confirmation**, then runs `python -m app.infra.schema
    --database-url-env DIRECT_URL`.
  - Check with a read-only query, no values printed: two tables, 1 key row, 0 consent rows, 3
    functions.
  - Covers: C18, C19.
- [ ] K4: Channel workflow A (plan Step 4).
  - Make the node changes through the MCP. The settings stay "save nothing", except
    `saveManualExecutions: true` during the pinned runs. This exception was approved by the human
    on 2026-11-22 as an extension of SPEC-005 A4.
  - Make one pinned run per scenario, with synthetic data only. Then set `saveManualExecutions:
    false` and read the settings back.
  - Check:
    - each scenario takes the expected path, text and keyboard;
    - B is called only in the two consented text runs, with `question` only;
    - "Detectar urgencia", "Clasificar" and "Decidir" carry their modules;
    - A's final settings are none, none, false and false.
  - **Reminder:** the human deletes the synthetic A executions and the B executions they created
    from the editor.
  - Covers: C1–C16 and C21 (wiring).
- [ ] K5 **[humano]**: Publish and test from Telegram (plan Step 5).
  - The human publishes A and sends the acceptance messages from an account with no consent
    record.
  - The agent:
    - checks the `consent` table read-only (status, version and date only);
    - checks B's executions;
    - scans B's new executions and the `consent` table for the account's identifiers;
    - **after asking**, inserts the two synthetic `revoked` rows and checks the purge.
  - Covers: acceptance criteria 1–9.
- [ ] K6: Exports and docs (plan Step 6).
  - Export A with the `shared` block removed and run the scan for secrets, personal data and the
    key.
  - Check that both Node tests are green with every sync check run.
  - Update the README "Demo" section and `specs/index.md`.
  - Covers: C26, C27; acceptance criteria 10–11.
