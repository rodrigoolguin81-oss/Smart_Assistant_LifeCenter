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

- [x] E0: Preflight, read-only (plan Step 0; G21).
  - Done 2026-11-22. Only read-only connections were opened; nothing was created or changed.
  - **Hosts and branches** (from `.env`: host and user only; no password or URL printed):

    | | Host | Neon branch |
    |---|---|---|
    | `DIRECT_URL` (main) | `ep-steep-resonance-…` | `br-crimson-scene-…` |
    | `TEST_DATABASE_URL` | `ep-blue-firefly-…` | `br-cool-feather-…` |

    - The hosts differ.
    - Both are in the same Neon project, on two different branches.
    - Both use user `neondb_owner` and database `neondb`, which is why only the host tells them
      apart (AGENTS.md preflight).
  - **n8n credential:** not used by this spec (G22). `Neon main` was last verified to point to
    `main` in SPEC-006 K5, by a write read back from `main`. It is not re-verified here, because
    that would need a write.
  - **On both branches:**
    - `btree_gist` 1.8 is **available and not installed**, so E2 installs it;
    - `pgcrypto` 1.4 is installed;
    - `consent_key` has 1 row;
    - **no `agenda_*` object** exists (0 relations, 0 functions, 0 types);
    - the server knows `Europe/Madrid`.
  - **Daylight saving time:** the server's Madrid offset at noon is `+1` on 27–28 March and `+2`
    from 29 March, and `+2` on 23–24 October and `+1` from 25 October. This confirms the 2026
    change dates for the DST tests.
  - **Finding for E2:** the session time zone (`TimeZone`) is **GMT** on both branches.
    - So every conversion to Madrid local time must use `AT TIME ZONE 'Europe/Madrid'`
      explicitly.
    - Never `::date` or `::time` on a `timestamptz`, which would use GMT, nor `SET TIME ZONE`.
    - n8n's Postgres sessions may have another time zone. The functions must give the same
      result whatever the session's time zone, and a test in E1 checks it by running with a
      different `TimeZone`.
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
- [x] E1: The tests first (plan Step 1).
  - Done 2026-11-22. `tests/infra/test_agenda_sql.py` has **43 test functions, 58 tests** once
    parametrized. It was **not run against Neon**: it compiles (`py_compile`), and its date and
    HOR-001 helpers were exercised locally.
  - **Dates are computed from today** (`date.today()`):
    - the base Monday is at least 2 weeks ahead and never in August;
    - `p_now` is the Friday before at 07:00 Madrid;
    - the DST tests use the next changes still ahead, now 28/03/2027 and 31/10/2027.

    This keeps synthetic appointments out of the real 30-day purge, and the tests do not age.
  - **Finding: HOR-001 has a third rule**, «Durante el mes de agosto la clínica abre solo por las
    mañanas, de 9:00 a 14:00», which the spec's weekday-only opening blocks do not cover.
    - The tests encode the agent's **proposal**: each opening block has a `months` set. In
      August, Monday to Friday is 9:00–14:00 only, and Saturday keeps 10:00–14:00.
    - **Accepted by the human on 2026-11-22** (clarifications Q15). The Saturday reading is an
      interpretation of example data, to confirm with the clinic (DEP-03). Spec G4 and the plan
      are updated.
  - The `reapplying` tests are excluded from E2's red run, so that run creates nothing.
  - Write `tests/infra/test_agenda_sql.py`, covering every acceptance criterion of the spec,
    including NFR-07, the per-subject limit, daylight saving time and HOR-001, and the check that the
    public `agenda_free_slots` and `agenda_book` have no `p_now` parameter (the tests use the
    internal `_at` versions).
  - Only write it here: **do not run it against Neon** until E2 is confirmed.
  - Check: it compiles locally (`py_compile`), and every criterion maps to at least one test.
  - Covers: G19 and the acceptance criteria.
- [x] E2 **[confirmación]**: `003_agenda.sql` on the test branch (plan Step 2).
  - Done 2026-11-22, after the human saw the summarized SQL, the exact commands and the host
    (`ep-blue-firefly-…`, the test branch) and confirmed. **Main was not touched.**
  - **`app/infra/sql/003_agenda.sql`** (343 lines, idempotent):
    - `btree_gist`, then 6 configuration tables seeded with `ON CONFLICT DO NOTHING` and
      `agenda_appointments`, which carries the two exclusion constraints and a role trigger;
    - `REVOKE … FROM PUBLIC`;
    - 7 functions: `agenda_subject`, `agenda_purge`, `agenda_slot_problem`,
      `agenda_free_slots_at`, `agenda_book_at`, and the public `agenda_free_slots` and
      `agenda_book`, which take no time parameter.
    - It has no `DROP`, `TRUNCATE` or write on `kb_fragments`, `consent` or `consent_key`.
  - **Red first.** The run excluded the `reapplying` tests and the file-exists test, so nothing
    was created. Result: 54 failed, 1 passed, 3 deselected.
    - Every failure was a missing agenda object: `UndefinedFunction` on `agenda_book_at`,
      `agenda_free_slots_at`, `agenda_subject` and `agenda_free_slots`, `UndefinedTable` on the
      `agenda_*` tables, or an assertion that found no columns or functions.
    - The one that passed is "no new key table", correct before the schema.
  - **Schema applied:** "Esquema aplicado en ep-blue-firefly-….neon.tech (TEST_DATABASE_URL)."
  - **Green at the first run.** `test_agenda_sql.py`: **58 passed** (40 s), with no change to the
    SQL. All of `tests/infra`: **117 passed** (SPEC-002 and SPEC-006 unaffected).
  - **Afterwards** (read-only, test branch):
    - 0 appointments and 0 closures, so the cleanup worked;
    - `consent` has 0 rows and `consent_key` 1;
    - `horizon` is back to 30 days after the "keeps changed values" test.
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
