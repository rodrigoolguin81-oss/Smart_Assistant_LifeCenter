---
type: tasks
spec_id: SPEC-008
title: move and cancel — Task Breakdown
description: Ordered, test-first tasks for moving and cancelling from Telegram — read-only preflight (hosts, the «Neon main» credential, the state of A and B), the JS modules, 005_move_cancel.sql on the test branch and main, A's change steps with pinned data, the Telegram test, and exports and docs.
tags: [tasks, move, cancel, SPEC-008]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: null }
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

- [ ] M0 **[humano for the credential]**: Preflight, read-only (plan Step 0; MC32).
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
- [ ] M1: `citas.js` and `consentimiento.js` extended, with their tests (plan Step 1; MC1–MC20,
  MC27–MC29).
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
- [ ] M2 **[confirmación]**: `005_move_cancel.sql` on the test branch (plan Step 2; MC21–MC23,
  MC30).
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
