---
type: tasks
spec_id: SPEC-004
title: agenda — Task Breakdown
description: Ordered, test-first tasks to build the project's own agenda in Neon — read-only host preflight, SQL tests, 003_agenda.sql on the test branch, main after confirmation, and docs.
tags: [tasks, agenda, SPEC-004]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# agenda — Tasks

Same pattern as SPEC-006 K0–K3. **Nothing is touched before the plan is approved.**

- One task at a time, with the human's confirmation in between.
- Steps marked **[confirmación]** wait for the human's go-ahead before running anything against
  Neon that creates or changes objects.
- No n8n change in this spec.
- Nothing is committed unless the human asks.

- [ ] E0: Preflight, read-only (plan Step 0; G21).
  - Print only the hosts of `DIRECT_URL` and `TEST_DATABASE_URL`, and check that they differ and
    are two branches (`neon.branch_id`) of the same project.
  - Record that this spec uses no n8n credential, and that `Neon main` was last verified to point
    to `main` in SPEC-006 K5.
  - On both branches, check:
    - whether `btree_gist` is available or installed;
    - that `pgcrypto` is installed;
    - that `consent_key` has 1 row;
    - that no `agenda_*` object exists yet;
    - that the server knows Europe/Madrid, with its 2026 changes on 29 March and 25 October.
  - Check: the findings are recorded here, and nothing was created or changed.
- [ ] E1: The tests first (plan Step 1).
  - Write `tests/infra/test_agenda_sql.py`, covering every acceptance criterion of the spec,
    including NFR-07, the per-subject limit, daylight saving time and HOR-001, and the check that the
    public `agenda_free_slots` and `agenda_book` have no `p_now` parameter (the tests use the
    internal `_at` versions).
  - Only write it here: **do not run it against Neon** until E2 is confirmed.
  - Check: it compiles locally (`py_compile`), and every criterion maps to at least one test.
  - Covers: G19 and the acceptance criteria.
- [ ] E2 **[confirmación]**: `003_agenda.sql` on the test branch (plan Step 2).
  - Write `app/infra/sql/003_agenda.sql`.
  - **Before running anything,** show the human the full SQL and the exact commands, and check
    the target host.
  - Run, in order:
    1. the tests red (those that apply the schema are excluded);
    2. the schema on `TEST_DATABASE_URL`;
    3. the tests green;
    4. all of `tests/infra`.
  - Check: every test is green, the key is never printed, and the test branch is left with no
    synthetic appointment or closure.
  - Covers: G1–G18.
- [ ] E3 **[confirmación]**: `main` (plan Step 3; G20).
  - Show the command, the host and the read-only check, and wait.
  - Run, in order: the check before, the schema on `DIRECT_URL`, the check after.
  - Check:
    - `kb_fragments` is unchanged (rows and md5);
    - `consent` is unchanged (count);
    - the key is unchanged (compared inside the script, never printed);
    - the configuration rows are present;
    - there are 0 appointments.
  - Covers: G2, G20.
- [ ] E4: Docs (plan Step 4; G23).
  - Add the README "Agenda" subsection: what it is, where to change the example values, how to
    apply the schema, reception's read-only query, and the limitations.
  - Update `specs/index.md`, and mark spec, plan and tasks implemented.
  - Check: the acceptance criteria are ticked, with notes where they were checked.
