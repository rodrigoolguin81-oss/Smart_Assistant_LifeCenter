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

- [x] K0: Facts, read-only (plan Step 0).
  - Done 2026-11-22. Nothing was created or changed: read-only connections to Neon, and reads of
    the installed n8n package.
  - **Roles** (read from `.env`, user name only; no password or URL printed):
    - `DIRECT_URL`, `DATABASE_URL` (pooled) and `TEST_DATABASE_URL` all use **`neondb_owner`**.
      The test branch has a different host from main.
    - `Neon main` was built from the parts of `DIRECT_URL` (human), so n8n uses `neondb_owner`
      too. That role owns `kb_fragments` and has `CREATE` on schema `public`, so it can create
      and call the functions; no `GRANT` is needed.
    - It is not a superuser, but it is a member of `neon_superuser`, which is what Neon requires
      to run `CREATE EXTENSION`.
    - The same role that n8n uses can read `consent_key`. `REVOKE … FROM PUBLIC` does not change
      that; it is the accepted limitation (spec, Known limitations).
  - **Neon:** PostgreSQL 18.7 on both branches.
    - `pgcrypto` 1.4 is **available and not installed** on the test branch or on main.
    - `consent` and `consent_key` do not exist on either.
  - **n8n 2.48.4:**
    - In the Telegram node, the inline-keyboard button's `callback_data` is a plain string field
      without `noDataExpression`, so it accepts expressions. Its description states the limit:
      "1-64 bytes".
    - `$('<node>').isExecuted` is implemented in `n8n-workflow`'s data proxy
      (`workflow-data-proxy.js`), which Code nodes use for `$()`. n8n's own error message
      suggests it for nodes that may not have run.
  - Check that `pgcrypto` is available and installed on the test branch and on main.
  - Read the role names in `DIRECT_URL` and `TEST_DATABASE_URL` from `.env`, without printing
    the password or the full URL. `Neon main` was created from the parts of `DIRECT_URL`
    (human, 2026-11-22), so it uses the same role.
  - Check in the n8n node types: expressions in the Telegram node's `callback_data`, and
    `isExecuted` in Code nodes.
  - Check: the findings are recorded here, and nothing was created or changed.
  - Covers: preconditions of C18, C19 and Step 4.
- [x] K1: `consentimiento.js` and its Node test (plan Step 1).
  - Done 2026-11-22. Nothing was touched in n8n or Neon.
  - **Red first.** `n8n/code/consentimiento.test.js` was written with the texts typed
    independently and a 28-case decision table. `consentimiento.js` at first held only the
    version, texts, labels and fixed `callback_data`, as in SPEC-003 U0. Red for the right
    reason:
    - 10 checks failed, all with "… is not implemented": `callbackAccept`, `parseCommand`,
      `parseCallback`, `classifyUpdate`, `isConsentInForce`, `formatDate` and `decide`;
    - the version, texts and button labels passed;
    - the sync checks were skipped ("Clasificar" and "Decidir" are not in A's export yet).
  - **Green.** With the functions added, every check passes.
  - **Choices made in the code:**
    - commands are exact but **case-insensitive** (`/Privacidad`, `/PRIVACIDAD`), as the human
      asked on 2026-11-22. The spec ("Command") was updated, the test got the cases first (red:
      2 checks), and then the `i` flag made it green;
    - **urgencies without consent**, checked end to end because the human asked (2026-11-22).
      The real `urgencias.js` runs with B's wiring on the urgent and severe acceptance messages,
      for three states: never accepted, withdrawn, and an older notice. Each time `decide()`
      returns the urgency reply with «Hablar con recepción», never `core` (B not called) and
      never the notice; the severe one carries the 112. It passed at once, because the
      behaviour was already there;
    - an empty text counts as "no text" (`other`), as A's current switch does;
    - `decide()` throws for the handoff route, so a wiring mistake is not silently answered
      (C12);
    - with consent in force, an urgency goes to B (`core`), so it is still recorded there (C3).
  - **Copies checked against the current workflows:** `TEXT_ONLY_TEXT` equals A's "Pedir texto"
    (D12), `ERROR_TEXT` is the text in B's "Error" (D7), and the «Hablar con recepción» label
    matches A's button.
  - **`urgencias.test.js`:** the sync check now covers both exports. B's runs; A's is skipped
    until A has "Detectar urgencia". Still GREEN: NFR-04 30/30, severe 8/8, 0 false positives
    and 0 false negatives.
  - First `n8n/code/consentimiento.test.js`: the texts, the decision table, the 64-byte limit,
    commands, version, dates and the sync check. It must be **red** for the right reason: only
    the missing functions fail.
  - Then `n8n/code/consentimiento.js`, until the test is green.
  - Point the sync check of `urgencias.test.js` at both exports. It stays green; A's check is
    skipped for now.
  - Check: both tests green; A's sync checks reported as skipped.
  - Covers: C1–C16 (logic), C22–C25.
- [x] K2 **[confirmación]**: Neon schema on the test branch (plan Step 2).
  - Done 2026-11-22, after the human saw the full SQL and the exact commands and confirmed. Run
    only against `TEST_DATABASE_URL` (host `ep-blue-firefly-…eu-central-1`, checked from `.env` to
    differ from `DIRECT_URL` and `DATABASE_URL`). **Main was not touched.**
  - **Files:**
    - `tests/infra/test_consent_sql.py`: 26 tests, fake ids `900001…` only, rows cleaned before
      and after each test, the key never selected (only its length);
    - `app/infra/sql/002_consent.sql`: `pgcrypto`, `consent_key`, `consent`, and the functions
      `consent_subject`, `consent_purge`, `consent_get`, `consent_accept` and `consent_revoke`;
    - `app/infra/schema.py`: a `__main__` with a required `--database-url-env` that prints only
      the host.
  - **Red first** (the tests that apply the schema were excluded, so nothing was created): 22
    failed and 2 passed (the CLI tests that need no database). Every failure was
    `UndefinedFunction` or `UndefinedTable` for the consent objects, plus one assertion on the
    missing columns.
  - **Schema applied:** `python -m app.infra.schema --database-url-env TEST_DATABASE_URL` →
    "Esquema aplicado en ep-blue-firefly-….neon.tech (TEST_DATABASE_URL)."
  - **Green:** `test_consent_sql.py` passed 26/26, and all of `tests/infra` passed 59/59, so the
    `kb_fragments` schema is unaffected.
  - **Afterwards** (read-only): `consent` has 0 rows on the test branch, so the cleanup worked,
    and `consent_key` has 1 row.
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
