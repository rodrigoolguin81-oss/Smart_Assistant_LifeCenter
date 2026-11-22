---
type: plan
spec_id: SPEC-006
title: consent — Technical Plan
description: How to build the consent step of the n8n demo — the consent module and its Node test, the Neon table, functions and key, the changes to the channel workflow A tested with pinned data, the Telegram test, and the exports and docs.
tags: [plan, consent, SPEC-006, n8n, neon]
status: implemented
sources: [./spec.md, ./clarifications.md, ../005-pseudonymized-log/plan.md, ../004-urgencies/plan.md]
generated: { by: claude-code, at: 2026-11-21T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# consent — Plan

Same order as SPEC-003 and SPEC-005 (human, 2026-11-21):

1. `consentimiento.js` with its Node test, test first.
2. The Neon table, functions and key, **only after the human confirms**.
3. The changes to A, tested with pinned data.
4. The human publishes and tests from Telegram.

B (`lifecenter-demo-core`) is not changed (clarifications A5).

## Architecture

```text
A  lifecenter-telegram-demo   (saves NO executions)
   Telegram Trigger → Clasificar (consentimiento.js: route = {kind, fromId, chatId, …})
     → ¿Qué ha llegado?  (Switch on route.kind)
        ├─ Recepción (handoff) → Confirmar botón → Responder recepción (D8)          [unchanged]
        ├─ Consentimiento (accept / reject / withdraw / unknown button)
        │     → Confirmar botón de consentimiento ─────────────────┐
        ├─ Comando (/start, /privacidad) ──────────────────────────┤
        ├─ Otro (no text) ─────────────────────────────────────────┤
        └─ Texto → Seudonimizar → Detectar urgencia (urgencias.js) ┤
                                                                   ▼
                    Consultar consentimiento (Neon: consent_get(from.id)) ─ ok / error ─┐
                                                                                         ▼
                    Decidir (consentimiento.js: action, text, keyboard)
                      → ¿Qué hacer?  (Switch on action)
                          ├─ core     → Llamar al núcleo ──(question only)──▶ B
                          │               → Componer respuesta ───────────────┐
                          ├─ accept   → Guardar aceptación (consent_accept) ──┤ → Tras guardar ┐
                          ├─ withdraw → Guardar retirada (consent_revoke) ────┘                │
                          └─ reply ───────────────────────────────────────────────────────────┤
                                                                                               ▼
                    ¿Qué teclado?  (Switch on keyboard)
                      → Responder (none) | Responder con botón (handoff)
                      | Responder con aviso (Acepto / No acepto) | Responder con retirar

Neon (eu-central-1)
   consent_key (one row, the key; never leaves the database)
   consent (subject, status, text_version, decided_at)
   consent_get / consent_accept / consent_revoke  (each purges revoked rows > 30 days first)
```

## Step 0: Facts, read-only

Nothing is created or changed in this step.

- **`pgcrypto`:** check that it is available in Neon (`pg_available_extensions`) on the test
  branch (`TEST_DATABASE_URL`) and on main, and whether it is already installed.
- **Roles:** record the name of the role behind `DIRECT_URL` and `TEST_DATABASE_URL`, read from
  `.env` without printing the password or the full URL.
  - The human created the n8n credential `Neon main` from the parts of `DIRECT_URL` (2026-11-22),
    so it uses the same role. That role runs the schema and calls the functions, so no `GRANT`
    is needed.
  - If the Telegram test in Step 5 still showed the D7 path on the consent lookup, the functions
    would get a `GRANT EXECUTE`.
- **n8n:** confirm in the node types that the Telegram node accepts expressions in
  `callback_data`, and that `$('Detectar urgencia').isExecuted` is available in Code nodes on
  n8n 2.48.4.

## Step 1: `n8n/code/consentimiento.js` and its Node test (TDD)

Paste-ready like `urgencias.js`: a plain script body with no `require`, so the test loads it
with `new Function` and the Code nodes carry it verbatim (C23).

**Constants.**

- `CONSENT_TEXT_VERSION = '1'`.
- The texts, as approved:
  - `CONSENT_NOTICE`, `ACCEPTED_TEXT`, `REJECTED_TEXT`, `REVOKED_TEXT`, `STATUS_ACCEPTED`
    (with `{fecha}`) and `STATUS_NONE`;
  - copies of the CHG-001 texts the module now composes: D7 `ERROR_TEXT` and D12
    `TEXT_ONLY_TEXT`.
- The button labels and `callback_data` values:
  - `handoff`, as today;
  - `consent:accept:<version>`, `consent:reject:<version>`, `consent:withdraw`.

  All fit in 64 bytes (C7).

**Functions.**

- `parseCommand(text)` returns `'start'`, `'privacidad'` or `null`. The text must be exactly the
  command, optionally followed by `@<bot>`, with surrounding spaces ignored and no other text.
- `parseCallback(data)` returns `{ kind: 'handoff' | 'accept' | 'reject' | 'withdraw' |
  'unknown_button', version }`.
- `classifyUpdate(update)` returns `route = { kind, fromId, chatId, callbackQueryId, version }`:
  - `fromId` comes from `message.from.id` or `callback_query.from.id`, as a string;
  - `chatId` comes from the message or from the callback's message;
  - `kind` is one of `handoff`, `accept`, `reject`, `withdraw`, `unknown_button`, `start`,
    `privacidad`, `text` or `other`.
- `isConsentInForce(row)`: true only for `status = 'accepted'` and `text_version =
  CONSENT_TEXT_VERSION` (C22).
- `formatDate(decidedAt)`: `dd/mm/aaaa` in Europe/Madrid.
- `decide({ route, urgency, consent, lookupFailed })` returns
  `{ action: 'core' | 'reply' | 'accept' | 'withdraw', text, keyboard: 'none' | 'handoff' |
  'consent' | 'withdraw' }`. `urgency` is the output of "Detectar urgencia", or `null` if the
  node did not run.

**Decision table** (`decide`; "in force" is `isConsentInForce`; "failed" is `lookupFailed`):

| Route | Condition | Result |
|---|---|---|
| `text` | urgency `urgent`/`severe` and (not in force or failed) | reply: the urgency text, keyboard `handoff` (C2, C6) |
| `text` | in force | `core` (C3) |
| `text` | urgency `none`, failed | reply: `ERROR_TEXT`, `handoff` (C6) |
| `text` | urgency `none`, not in force | reply: `CONSENT_NOTICE`, `consent` (C4) |
| `other` | in force | reply: `TEXT_ONLY_TEXT`, `none` (C5, D12) |
| `other` | not in force | reply: `CONSENT_NOTICE`, `consent` (C5) |
| `start` | not in force | reply: `CONSENT_NOTICE`, `consent` (C14) |
| `start`, `privacidad` | in force | reply: `CONSENT_NOTICE` + `STATUS_ACCEPTED` with the date, `withdraw` (C15) |
| `privacidad` | not in force | reply: `CONSENT_NOTICE` + `STATUS_NONE`, `consent` (C15) |
| `accept` | current version | `accept`: `ACCEPTED_TEXT`, `none` (C8) |
| `reject` | current version | reply: `REJECTED_TEXT`, `none` (C9) |
| `accept`, `reject` | older version, or `unknown_button` | reply: `CONSENT_NOTICE`, `consent` (C11) |
| `withdraw` | any | `withdraw`: `REVOKED_TEXT`, `none` (C10) |
| any except `text` with an urgency | failed | reply: `ERROR_TEXT`, `handoff` (C6) |

`handoff` never reaches `decide`: it keeps its own unchanged branch (C12). The urgency text comes
from "Detectar urgencia" (`composeUrgencyReply`). It is not re-written in this module.

**Test** `n8n/code/consentimiento.test.js` (no dependencies; exits non-zero on failure):

- the texts, typed independently in the test (as in `urgencias.test.js`);
- every row of the decision table;
- the 64-byte limit for every `callback_data`;
- command parsing: `/start`, `/privacidad`, with `@bot`, with spaces, with extra text, and case;
- the version rule;
- `formatDate` across a summer and a winter date;
- a sync check: every node of A's export whose name is in the list ("Clasificar", "Decidir")
  has `jsCode` starting with the module. It is skipped while the export does not have them yet.

**`urgencias.test.js`:** the sync check reads **both** exports (C25). A's check is skipped until
A has "Detectar urgencia".

## Step 2: Neon schema on the test branch, with its test [asks for confirmation first]

**`app/infra/sql/002_consent.sql`** is idempotent and applied by the existing
`app/infra/schema.py`:

- `CREATE EXTENSION IF NOT EXISTS pgcrypto`;
- `consent_key`: a single row (`singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton)`,
  `key bytea NOT NULL`):
  - filled by `INSERT … VALUES (gen_random_bytes(32)) ON CONFLICT DO NOTHING`, so the key is
    created inside Neon, never printed, and **kept** on re-runs (C19);
  - `REVOKE ALL ON consent_key FROM PUBLIC`;
- `consent`: `subject text PRIMARY KEY`, `status text NOT NULL CHECK (status IN ('accepted',
  'revoked'))`, `text_version text NOT NULL`, `decided_at timestamptz NOT NULL` (C17);
- the functions, all `plpgsql`, with `SET search_path = public, pg_temp`:
  - `consent_subject(p_from_id text)`, internal:
    `encode(hmac(convert_to(p_from_id, 'UTF8'), key, 'sha256'), 'hex')` (C18);
  - `consent_purge()`, internal: deletes `revoked` rows with `decided_at < now() - interval
    '30 days'` (C20);
  - `consent_get(p_from_id text)` → `(status, text_version, decided_at)`: purge, then select;
  - `consent_accept(p_from_id text, p_version text)`: purge, then upsert `accepted`, `now()`;
  - `consent_revoke(p_from_id text)`: purge, then set `revoked`, `now()` on an `accepted` row.

  n8n only ever calls these three, passing `from.id` as a query parameter (`$1`).

**`schema.py`** gains a `__main__` with `--database-url-env`, like `kb_ingest`, so the schema can be
applied without re-ingesting `kb/`.

**Test first:** `tests/infra/test_consent_sql.py`, against `TEST_DATABASE_URL` only (the existing
`conftest.py` refuses main). It uses fake ids `900001…` and deletes their rows at the end. It checks:

- the subject is 64 hex characters and is not the id;
- `consent_get` of an unknown id returns nothing;
- `accept`, then `get`, gives `accepted` with the version;
- a second `accept` with another version leaves **one** row;
- `revoke` gives `revoked`;
- a synthetic `revoked` row dated 31 days ago is purged by the next call, and one dated 29 days
  ago remains;
- no column of `consent` contains the id;
- re-applying the schema keeps the key: the same id gives the same subject.

**Before running it the agent asks for confirmation**, because it creates `pgcrypto`, the tables
and the key on the test branch.

## Step 3: Neon schema on main [asks for confirmation first]

After Step 2 is green and the human confirms:
`python -m app.infra.schema --database-url-env DIRECT_URL`.

Check with a read-only query, printing no values:

- the two tables exist;
- `consent_key` has 1 row;
- `consent` has 0 rows;
- the three functions exist.

## Step 4: Channel workflow A, changed through the MCP, tested with pinned data

**Nodes**, following the architecture above:

- **New:**
  - "Clasificar": the module plus `return { json: { ...$json, route: classifyUpdate($json) } }`,
    so "Seudonimizar" keeps reading `$json.message` unchanged;
  - "Confirmar botón de consentimiento": `answerQuery` (C13);
  - "Detectar urgencia": `urgencias.js` and B's wiring, byte for byte;
  - "Consultar consentimiento": Postgres on `Neon main` with an error output (C6). The query
    is `SELECT g.status, g.text_version, g.decided_at FROM (SELECT 1) AS one LEFT JOIN
    consent_get($1) AS g ON true`, which always returns exactly one row (nulls when there is no
    record). "Guardar aceptación" and "Guardar retirada" use the same shape.
    - **Changed in K4 (2026-11-22):** the plan had "Always output data" on. In n8n 2.48.4
      (`ensureAlwaysOutputData` in `workflow-execute.js`) that setting adds an empty item to the
      main output even when the item went to the error output. "Decidir" would then run twice
      and send two replies, so the one-row query replaces it.
  - "Decidir": the module plus the wiring that reads `route`, the urgency (if
    `isExecuted`), the row or the error, and adds `chatId`;
  - "¿Qué hacer?";
  - "Guardar aceptación" and "Guardar retirada", Postgres, each with an error output;
  - "Tras guardar": the decision as it was, or `ERROR_TEXT` with `handoff` if the write failed;
  - "¿Qué teclado?";
  - "Responder con aviso", with «Acepto» / «No acepto» and `callback_data` built from
    `CONSENT_TEXT_VERSION`;
  - "Responder con retirar".
- **Changed:**
  - "¿Qué ha llegado?" now switches on `route.kind`;
  - "Llamar al núcleo" reads `question` from "Seudonimizar";
  - "Componer respuesta" also sets `keyboard` from `handoff`;
  - "¿Ofrecer recepción?" is replaced by "¿Qué teclado?".
- **Removed:** "Pedir texto". D12 is composed by "Decidir".
- **Unchanged:** Telegram Trigger, "Seudonimizar", "Confirmar botón", "Responder recepción",
  "Responder" and "Responder con botón" (they read `chatId` and `text`), and every SPEC-005
  setting (C21).

**Test with pinned data.** A saves no manual executions. **Approved by the human (2026-11-22)** as
an extension of the SPEC-005 exception A4, recorded in the SPEC-005 clarifications:

1. Set `saveManualExecutions: true` while the pinned runs are made, with **synthetic** updates
   only: fake `from.id`/chat ids `900001…`, test names, no real data.
2. Make **one run per scenario**. Each has one Telegram update, and the consent lookup is pinned
   with no row, an accepted row of the current version, or an accepted row of an older version.
   Pinning per node would not pair correctly with several items in one run. Scenarios:
   - without consent: text, urgent text, sticker, `/start`, `/privacidad`, «Acepto» current,
     «Acepto» old, «No acepto», «Hablar con recepción»;
   - with consent: text (calls B), urgent text (calls B), `/start`, `/privacidad`, «Retirar
     consentimiento», sticker.
3. Check each run's path, action, text, keyboard and chat id. Check that B is called **only** in
   the two consented text runs, with `question` only.
4. Set `saveManualExecutions: false` immediately, before anything is published, and read the
   settings back.
5. The human deletes those synthetic executions of A (and the B executions they created) from the
   editor.

Not covered by the pinned runs: the real Neon calls and their error outputs. `test_workflow`
pins Postgres nodes. The calls are covered by Step 2's test, and the error outputs by the
decision table, a structural check of the wiring and the Telegram test.

## Step 5: Publish and test from Telegram [human]

The human publishes **A** (B does not change). Then, from a team account with no consent record,
the human sends the spec's acceptance messages in order. The agent then:

- reads the `consent` table read-only after «No acepto», «Acepto» and «Retirar», printing status,
  version and date only, never the subject;
- lists executions through the MCP: B entries only for the consented text messages;
- scans the new B executions and the `consent` table for the test account's id, chat id, profile
  name and username;
- inserts two synthetic `revoked` rows (31 and 29 days old) under made-up subjects, triggers one
  lookup and checks the purge. **The agent asks before writing these rows on main.**

## Step 6: Exports and docs

- Export A to `n8n/workflows/lifecenter-telegram-demo.json` with the `shared` block removed, and
  run the secret, personal-data and key scan (C26). B's export does not change.
- Both Node tests are green, with every sync check run (C25).
- README "Demo":
  - the consent step and `/privacidad`;
  - the one-off `python -m app.infra.schema --database-url-env DIRECT_URL` before publishing A
    on a new instance;
  - the SPEC-006 limitations (C27).
- `specs/index.md`.

## Requirement → component map

| Requirement | Component |
|---|---|
| C1–C6 | "Seudonimizar", "Detectar urgencia" (A), "Consultar consentimiento", `decide` (Steps 1, 4) |
| C7–C13 | `parseCallback`, `callback_data` constants, "Confirmar botón de consentimiento", "Guardar…", "Tras guardar" |
| C14–C16 | `parseCommand`, `classifyUpdate`, `decide` |
| C17–C20 | `002_consent.sql`, `test_consent_sql.py` (Steps 2–3) |
| C21 | A's settings, "Llamar al núcleo" inputs (Step 4) |
| C22 | `CONSENT_TEXT_VERSION`, `isConsentInForce` |
| C23–C25 | `consentimiento.js`, both Node tests and their sync checks |
| C26, C27 | Step 6 |
