---
type: tasks
spec_id: SPEC-007
title: booking — Task Breakdown
description: Ordered, test-first tasks for booking from Telegram — read-only preflight with the Neon main credential host, the JS modules, agenda_my_next on the test branch and main, offer_booking in B, A's booking branch with pinned data, the Telegram test, and exports and docs.
tags: [tasks, booking, SPEC-007]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: null }
stale_after: null
---

# booking — Tasks

Same pattern as SPEC-006 and SPEC-004. **Nothing is touched before the plan is approved.**

- One task at a time, with the human's confirmation in between.
- **[confirmación]** steps wait for the human's go-ahead before anything that creates or changes
  objects in Neon.
- **[humano]** steps need the human.
- The workflows are only changed in R4 and R5, as drafts. The human publishes, **B before A**.
- Nothing is committed unless the human asks.

- [ ] R0 **[humano for the credential]**: Preflight, read-only (plan Step 0; BK26).
  - **Agent:**
    - print the hosts of `DIRECT_URL` and `TEST_DATABASE_URL` and their `neon.branch_id`;
    - check that the 7 SPEC-004 functions exist on both branches, that `main`'s agenda
      configuration and appointment count are unchanged, and that `agenda_my_next` does not
      exist yet;
    - record what the MCP lists about `Neon main` (name, type, id, last update if shown);
    - check that the A and B exports in git are the published versions, and how the Telegram
      node builds the inline keyboard.
  - **Human, in the n8n UI, without saving:** open «Neon main» and check:
    - Host = `ep-steep-resonance-…`;
    - Database `neondb`, User `neondb_owner`;
    - SSL `require`, with the three certificate fields empty.

    Close it without saving, and report what was seen.
  - Check: the findings are recorded here, and nothing was created or changed.
- [ ] R1: `citas.js`, the `consentimiento.js` extension, and their tests (plan Step 1; BK1–BK20,
  BK23).
  - **Red first:**
    - `n8n/code/citas.test.js` and `evals/booking_phrases.yaml`, with the positives and the
      negatives of BK3;
    - the new cases in `consentimiento.test.js`;
    - a `citas.js` holding only its constants, as in SPEC-003 U0 and SPEC-006 K1.
  - Then the functions, until green. `urgencias.test.js` must stay green.
  - Check:
    - all three Node tests green;
    - every positive phrase matches and 0 negatives do;
    - every callback ≤ 64 bytes;
    - the A sync checks are skipped until R5.
- [ ] R2 **[confirmación]**: `004_booking.sql` on the test branch (plan Step 2; BK19, BK24).
  - First `tests/infra/test_booking_sql.py`, then the SQL.
  - **Before running anything,** show the SQL, the exact commands and the host.
  - Run: red (nothing created), the schema, green, then all of `tests/infra`.
- [ ] R3 **[confirmación]**: `main` (plan Step 3; BK24).
  - Show the command, the host and the read-only check, and wait.
  - Run: the check before, the schema on `DIRECT_URL`, the check after.
  - **Stop if** `kb_fragments`, `consent`, `consent_key` or the agenda changed.
- [ ] R4: B, `offer_booking` (plan Step 4; BK6, BK7).
  - Change the draft through the MCP, and make one pinned run per case.
  - Check:
    - `true` only for TAR or TRA answers;
    - `false` for HOR-only answers, abstentions and urgencies;
    - "Resultado" returns it;
    - B's draft has no pinned data left;
    - its settings are unchanged.
- [ ] R5: A, the booking branch (plan Step 5; BK1–BK22).
  - Before changing anything, list the nodes to add, change and remove, and wait.
  - Change the draft through the MCP.
  - Make the pinned runs under the A4 extension: fake ids `900301…`, one run per scenario.
  - Afterwards:
    - `saveManualExecutions: false`;
    - **no pinned data** in A or B, checked with `get_workflow_details` and a CLI export;
    - the list of executions for the human to delete.
  - Check: every scenario of plan Step 5 behaves as expected, and B is called only where planned.
- [ ] R6 **[humano]**: Publish **B, then A**, and test from Telegram (plan Step 6).
  - The agent checks `main`'s appointments (read-only, no subject), B's executions, and the
    dynamic keyboard. If the keyboard fails, apply the fallback.
  - Covers: the Telegram acceptance criteria.
- [ ] R7: Exports and docs (plan Step 7; BK27).
  - Export A and B with the `shared` block removed, and run the scan.
  - Run every Node and SQL test.
  - Update the README, `specs/index.md`, and mark spec, plan and tasks implemented.
