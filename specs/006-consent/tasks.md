---
type: tasks
spec_id: SPEC-006
title: consent — Task Breakdown
description: Ordered, test-first tasks to build the consent step of the n8n demo — facts, consent module and Node test, Neon schema on the test branch and on main, changes to A with pinned data, Telegram test, and exports and docs.
tags: [tasks, consent, SPEC-006]
status: implemented
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
      too.
    - **Correction (K5, 2026-11-22):** only the **user** was checked, not the host. The
      credential actually pointed to the **test branch**. See K5; AGENTS.md now requires
      checking the host in this first task. That role owns `kb_fragments` and has `CREATE` on schema `public`, so it can create
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
- [x] K3 **[confirmación]**: Neon schema on main (plan Step 3).
  - Done 2026-11-22, after the human confirmed. Beforehand the human was shown the exact command,
    the main host (`ep-steep-resonance-…eu-central-1`, which differs from the test host), the
    proof that re-applying `001_kb_fragments.sql` only uses `IF NOT EXISTS`, and the read-only
    check.
  - **Read-only check, before and after.** The check printed only counts, existence and an md5
    digest of the whole `kb_fragments` table, no values:

    | | Before | After |
    |---|---|---|
    | `kb_fragments` rows | 9 | 9 |
    | `kb_fragments` md5 | `73ef6b7e…cdf5d` | `73ef6b7e…cdf5d` (same) |
    | `consent` | does not exist | exists, 0 rows |
    | `consent_key` | does not exist | exists, 1 row |
    | `consent_*` functions | 0 of 5 | 5 of 5 |
    | `pgcrypto` | not installed | installed |

  - **Applied:** `python -m app.infra.schema --database-url-env DIRECT_URL` → "Esquema aplicado en
    ep-steep-resonance-….neon.tech (DIRECT_URL)."
  - **Operating rule** added to the spec (Known limitations): main's key must never be
    regenerated or deleted.
  - **The agent asks for confirmation**, then runs `python -m app.infra.schema
    --database-url-env DIRECT_URL`.
  - Check with a read-only query, no values printed: two tables, 1 key row, 0 consent rows, 3
    functions.
  - Covers: C18, C19.
- [x] K4: Channel workflow A (plan Step 4).
  - Done 2026-11-22 on A's **draft**; nothing published. The published version stays
    `3a4054b9…` (11 nodes, SPEC-005); the draft is `5b41b4ee…`.
  - **How it was built:**
    - A script generated the operations from the repo files.
    - They were applied through the MCP in 5 updates: the structure, the code of "Clasificar",
      "Decidir" and "Detectar urgencia", and the settings.
    - **A temporary CLI export of the draft** (scratchpad, not the repo) showed the three code
      nodes **identical** to the generated code: `consentimiento.js` and `urgencias.js` plus
      their wiring. The other new nodes have 0 differences from the generated parameters.
    - A has 21 nodes: 12 added, 4 changed, and "Pedir texto" and "¿Ofrecer recepción?" removed.
  - **Deviation from the plan:** no "Always output data". The three Postgres queries use a one-row
    `LEFT JOIN` instead (plan Step 4, note). The shape was checked on the test branch:
    `consent_get` of an unknown id gives one row of nulls.
  - **17 pinned runs** (approved extension of SPEC-005 A4; synthetic updates with ids
    `900001`–`900017`; trigger, Telegram and Postgres nodes pinned, so nothing was sent and Neon
    was not called). One run per scenario, checked from n8n's local database (read-only):

    | # | Exec. | Scenario | Result |
    |---|---|---|---|
    | 1 | 101 | text, no consent | notice, «Acepto / No acepto» (`consent:accept:1` / `consent:reject:1`); B not called |
    | 2 | 102 | urgent text, no consent | `URGENT_MESSAGE` + «Hablar con recepción», no notice; B not called |
    | 3 | 103 | sticker, no consent | notice |
    | 4 | 104 | `/start`, no consent | notice |
    | 5 | 105 | `/Privacidad`, no consent | notice + «Estado: no has aceptado este aviso.» + Acepto / No acepto |
    | 6 | 106 | «Acepto» v1 | "Guardar aceptación" → `ACCEPTED_TEXT` |
    | 7 | 107 | «Acepto» v0 | notice; nothing written |
    | 8 | 108 | «No acepto» v1 | `REJECTED_TEXT`; nothing written |
    | 9 | 109 | «Hablar con recepción» | D8 by its own branch; no lookup |
    | 10 | 110 → B 111 | text, consent | B with `question` only → 60 € with TAR-001 and both notices |
    | 11 | 112 → B 113 | severe text, consent | B → `SEVERE_MESSAGE` (112), B records `reason: urgency`, `severe` |
    | 12 | 114 | `/start`, consent | notice + «Estado: aceptaste este aviso el 21/11/2026.» + «Retirar consentimiento» |
    | 13 | 115 | `/privacidad`, consent | same as 12 |
    | 14 | 116 | «Retirar consentimiento» | "Guardar retirada" → `REVOKED_TEXT` |
    | 15 | 117 | sticker, consent | D12 |
    | 16 | 118 | text, lookup fails (pinned `{error}`) | D7 + «Hablar con recepción»; B not called |
    | 17 | 119 | «Acepto», write fails (pinned `{error}`) | "Tras guardar" → D7 + «Hablar con recepción» |

    - The `chatId` was the right one in every run.
    - B received **only** `question` in 111 and 113. Neither execution contains a test id,
      `chatId` or `first_name`.
    - Scenarios 16 and 17 pin the error item on the main output, so they check how "Decidir"
      and "Tras guardar" handle it. The real error outputs are checked structurally (wired to
      "Decidir" and "Tras guardar") and in K5.
  - **Afterwards:**
    - `saveManualExecutions` was set back to `false`. Read back with `get_workflow_details`:
      none, none, false, false.
    - **No pinned data** is left in the draft: there is no `pinData` field in
      `get_workflow_details` (`test_workflow` passes it per run), and the CLI export shows
      `pinData: null`.
    - No test id or "Prueba" appears anywhere in the draft.
  - **Executions for the human to delete** (2026-11-22, 15:35:46–15:37:55 UTC):
    - A: 101–110, 112 and 114–119 (17);
    - B: 111 and 113.
    - B execution 100 (14:31 UTC) is an ordinary message to the published bot, not part of K4.
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
- [x] K5 **[humano]**: Publish and test from Telegram (plan Step 5).
  - Done 2026-11-22.
  - **First Telegram test** (human, from 16:49 Madrid), all as expected:
    - the notice without consent;
    - «No acepto»;
    - an urgency without consent, with the 112;
    - `/privacidad` without accepting;
    - «Acepto», then 60 € with TAR-001;
    - `/Privacidad` in capitals, showing the date and «Retirar consentimiento»;
    - the withdrawal, the notice again, and «Acepto» at the end.

    The human had published A (`5b41b4ee…`) and deleted the 17 K4 executions of A and the 2 of
    B.
  - **Finding: `Neon main` pointed to the Neon test branch.**
    - The read-only check found **0 rows** in `consent` on `main`, and **1 row** (`accepted`,
      version 1, 16:54) on the test branch (`ep-blue-firefly-…`).
    - The credential shares user and database with `main` and differed only in the **host**,
      so K0, which checked only the user, missed it.
    - B's "Buscar en kb" also read the test branch. Its `kb_fragments` happened to equal
      `main`'s: 9 rows, same md5, HOR-001, TAR-001 and TRA-001. But `pytest tests/infra` (run in
      K2) drops and rewrites that table.
    - It is not known since when the credential pointed there.
  - **Fix (human, 2026-11-22):**
    - The host of `Neon main` was changed to `DIRECT_URL`'s (`ep-steep-resonance-…`).
    - **The browser had autofilled the SSL certificate fields** (CA Certificate, Client Private
      Key, Client Certificate). The human cleared them, and the connection test passes.
    - From Telegram, `/privacidad` then showed «no has aceptado», because `main` had no record.
      «Acepto» followed, and limpieza answered 60 € with TAR-001.
  - **Checks after the fix (agent, read-only; no subject or identifier printed):**
    - `consent` on `main`: **1 row, `accepted`, version 1** (22/11/2026 17:04). `consent_key`
      has 1 row.
    - The human's row on the test branch was deleted with the human's authorization. The host
      was shown and guarded first. `DELETE FROM consent` removed 1 row, and 0 rows are left.
      `main` keeps its row.
    - **B since 16:49 Madrid:** a single execution, 126 (`answered`). It received only
      `["question"]`, with no Telegram key (`chatId`, `chat`, `from`, `first_name`,
      `username`) and no id-like number. Messages without consent, buttons and commands
      created no B execution, as designed.
    - **A:** saves nothing. Its 10 rows in n8n's local database (120–125, 127–130) were already
      soft-deleted: this is the accepted SPEC-005 window of about 15 minutes. The published
      version is `5b41b4ee…` = the draft, with settings none / none / false / false and no
      pinned data.
  - **Not done, by the human's decision:** the two synthetic `revoked` rows in `main` to test
    the 30-day purge. The purge is covered by `test_consent_sql.py` on the test branch (K2).
  - **Operating notes added:**
    - README: `Neon main` must point to `main`, never to the test branch, with the certificate
      fields empty;
    - AGENTS.md: the first task of every spec that touches n8n or Neon checks each credential's
      host, not only the user.
  - The human publishes A and sends the acceptance messages from an account with no consent
    record.
  - The agent:
    - checks the `consent` table read-only (status, version and date only);
    - checks B's executions;
    - scans B's new executions and the `consent` table for the account's identifiers;
    - **after asking**, inserts the two synthetic `revoked` rows and checks the purge.
  - Covers: acceptance criteria 1–9.
- [x] K6: Exports and docs (plan Step 6).
  - Done 2026-11-22.
  - **Export of A:** `n8n/workflows/lifecenter-telegram-demo.json`, the published version
    `5b41b4ee…` (`versionId` = `activeVersionId`), with the `shared` block removed. It has 21
    nodes, no `pinData`, settings none / none / false / false, and credentials `Telegram
    LifeCenter Bot` and `Neon main`.
  - **Scan:** the README pattern for secrets, plus `neon.tech` and certificates, found nothing.
    There is no name, e-mail, test id `9000xx`, "Prueba", `first_name`/`username` value or
    id-like number, and no `consent_key`, `gen_random_bytes` or `hmac`.
  - **B unchanged:** its current definition equals the committed export (same `versionId`).
    The credential's host change does not appear in the workflow files, which reference the
    credential by id.
  - **Tests:** both GREEN, with every sync check run:
    - `consentimiento.test.js`: "Clasificar" and "Decidir" in A's export. The check now prints a
      line when it runs;
    - `urgencias.test.js`: "Detectar urgencia" in B's **and** A's exports; NFR-04 30/30.
  - **README "Demo":**
    - A's consent step and diagram;
    - the consent schema step and the rule never to regenerate the key;
    - the `Neon main` operating note;
    - the consent rows of "Try it";
    - the SPEC-006 limitations;
    - "Detectar urgencia" now lives in both workflows;
    - the consent tests in the export section.
  - **`specs/index.md`:** SPEC-006 implemented.
  - Export A with the `shared` block removed and run the scan for secrets, personal data and the
    key.
  - Check that both Node tests are green with every sync check run.
  - Update the README "Demo" section and `specs/index.md`.
  - Covers: C26, C27; acceptance criteria 10–11.
