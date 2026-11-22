---
type: tasks
spec_id: SPEC-007
title: booking — Task Breakdown
description: Ordered, test-first tasks for booking from Telegram — read-only preflight with the Neon main credential host, the JS modules, agenda_my_next on the test branch and main, offer_booking in B, A's booking branch with pinned data, the Telegram test, and exports and docs.
tags: [tasks, booking, SPEC-007]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
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

- [x] R0 **[humano for the credential]**: Preflight, read-only (plan Step 0; BK26).
  - Done 2026-11-22. Only reads were made: read-only connections to Neon, the MCP, n8n's local
    database (metadata only) and the installed n8n package. Nothing was created or changed.
  - **Neon:**

    | | `DIRECT_URL` (main) | `TEST_DATABASE_URL` |
    |---|---|---|
    | Host | `ep-steep-resonance-…` | `ep-blue-firefly-…` |
    | Branch | `br-crimson-scene-…` | `br-cool-feather-…` |
    | SPEC-004 functions | 7 of 7 | 7 of 7 |
    | `agenda_my_next*` | 0 (not created yet) | 0 |
    | Agenda configuration | 3/3/5/11/1, 0 closures | 3/3/5/11/1, 0 closures |
    | Appointments | 0 | 0 |
    | `consent` / `consent_key` | 1 / 1 | 0 / 1 |

    The hosts differ, and both are branches of the same project.
  - **The `Neon main` credential:**
    - **Human, in the n8n UI, without saving (2026-11-22):**
      - host `ep-steep-resonance-…`, database `neondb`, user `neondb_owner`;
      - SSL `require`, with **the three certificate fields empty**.

      That is `main`, the host of `DIRECT_URL`.
    - **MCP:** id `QvG6Gru4fDSLvtzu`, type `postgres`. The MCP does not show fields or dates.
    - **n8n's local database**, metadata only, with no credential data read: `updatedAt`
      22/11/2026 16:02 UTC. That is the SPEC-006 K5 fix, minutes before the acceptance that
      landed in `main` (17:04 Madrid). It has not changed since.
  - **Workflows:** A (`5b41b4ee…`, 21 nodes) and B (`711b573c…`, 11 nodes) are published. Draft
    = published = the `versionId` of the exports in git, so the exports are a valid rollback
    copy.
    - A's settings are none / none / false / false.
    - B saves everything, with its caller policy limited to A.
  - **Telegram node** (n8n 2.48.4, `GenericFunctions.js` line 78): the inline keyboard is read
    with `getNodeParameter('inlineKeyboard')` and built from `rows[].row.buttons[]`, so a single
    expression can return the whole keyboard (plan Step 5). That it really sends will only be
    confirmed in R6, because the Telegram nodes are pinned in the pinned runs.
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
- [x] R1: `citas.js`, the `consentimiento.js` extension, and their tests (plan Step 1; BK1–BK20,
  BK23).
  - Done 2026-11-22. Nothing was touched in n8n or Neon.
  - **Red first:**
    - `n8n/code/citas.test.js`, with 14 `prepare` cases and 21 `compose` cases;
    - `evals/booking_phrases.yaml`, with **25 positives and 25 negatives**, including the
      human's «tengo una cita el lunes», «¿cuánto cuesta una cita?», «cancelar mi cita» and
      «cambiar mi cita»;
    - 4 new checks in `consentimiento.test.js`.
    - `citas.js` first held only its texts, labels and types. Red: **10** checks of `citas.test.js`
      failed, all with "… is not implemented"; texts, labels, types and the dataset shape passed.
      The 4 new `consentimiento.test.js` checks failed: `/cita` not parsed, `bk:` not
      classified, no booking route, no `booking` action. `urgencias.test.js` stayed green.
  - **Green:**
    - `citas.test.js` is GREEN: phrases **25/25 positives, 0/25 negatives**, every type right,
      every callback ≤ 64 bytes, and dates correct across both DST changes.
    - `consentimiento.test.js`: every functional check is green. Its sync check with A's export
      is skipped with «hasta R5» while A has no booking nodes. A still carries the SPEC-006
      module, and the check runs again from R5 (human, 2026-11-22: nothing red in the commit).
    - `urgencias.test.js` is GREEN (NFR-04 30/30).
  - **Changes after the human's R1 review (2026-11-22):**
    - `LIMIT_TEXT` now reads «Ya tienes {tipo} el …». Every text uses the type with its article,
      taken from the type code, so `agenda_my_next` returns `type_code` (spec BK19).
    - The extra «Hablar con recepción» and «Pedir cita» buttons and the two queries are approved
      (spec BK19b).
    - **Order test.** «quiero cita, me sangra mucho la encía», «necesito una cita urgente, se me ha
      hinchado la cara», «quiero pedir cita, me duele muchísimo una muela» and «dame cita, se me ha
      roto un diente» each look like a booking phrase on their own. With the real `urgencias.js`
      they are urgent, and `bookingPhraseFor` sends them **to urgency, not to booking**.
    - Red first again: 3 checks failed. Then green.
  - **Choices made in the code:**
    - **«Hablar con recepción»** is on every booking message except the confirmation (Q8). The
      confirmation keeps exactly «Confirmar» · «Elegir otro hueco», as the spec says.
      `NO_APPOINTMENT_TEXT` also gets «Pedir cita».
    - **Ver más or a lost race with no slots left** gets `NO_SLOTS_TEXT`.
    - **Booking routes** add a `data` field (the command or the raw `callback_data`). The other
      routes keep their SPEC-006 shape, so the existing tests did not change.
    - **Queries:** `prepare()` needs only two, `agenda` and `book` (plan Step 5, note).
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
- [x] R2 **[confirmación]**: `004_booking.sql` on the test branch (plan Step 2; BK19, BK24).
  - Done 2026-11-22, after the human saw the full SQL, the exact commands and the host
    (`ep-blue-firefly-…`, the test branch) and confirmed. **Main was not touched.**
  - **`tests/infra/test_booking_sql.py`**, written first: 17 tests, fake ids `900401…`, dates
    computed from today, and the key never selected.
  - **`app/infra/sql/004_booking.sql`** holds only `agenda_my_next_at(from_id, now)` and the public
    `agenda_my_next(from_id)`, which return `(type_code, starts_at, ends_at)`. There is no table
    and no write statement.
  - **Red first** (the `reapplying` and file-exists tests were excluded, so nothing was created):
    15 failed. There were 14 `UndefinedFunction` on `agenda_my_next_at`, and 1 assertion that
    found no public signature.
  - **Schema applied:** "Esquema aplicado en ep-blue-firefly-….neon.tech (TEST_DATABASE_URL)."
  - **Green:** `test_booking_sql.py` **17 passed**. All of `tests/infra`: **134 passed**, with
    SPEC-002, SPEC-006 and SPEC-004 unaffected.
  - **Afterwards** (read-only, test branch): 0 appointments and 0 closures (cleanup worked),
    `consent` 0, `consent_key` 1, and 2 `agenda_my_next*` functions.
  - First `tests/infra/test_booking_sql.py`, then the SQL.
  - **Before running anything,** show the SQL, the exact commands and the host.
  - Run: red (nothing created), the schema, green, then all of `tests/infra`.
- [x] R3 **[confirmación]**: `main` (plan Step 3; BK24).
  - Done 2026-11-22, after the human confirmed. Beforehand the human was shown the command, the
    host (`ep-steep-resonance-…`, guarded by the script) and the read-only check.
  - **Read-only check, before and after.** It printed only counts, existence and comparisons.
    The fingerprints of `consent`, the key and the agenda configuration were computed in the
    database and compared inside the script. The state file was deleted afterwards.

    | | Before | After |
    |---|---|---|
    | `kb_fragments` | 9 rows, md5 `73ef6b7e…cdf5d` | same |
    | `consent` / `consent_key` | 1 / 1 | **unchanged** (fingerprints equal) |
    | Agenda | 3/3/5/11/1, 0 closures, 0 appointments | **unchanged** (fingerprint equal) |
    | SPEC-004 functions | 7 of 7 | 7 of 7 |
    | `agenda_my_next`, `agenda_my_next_at` | 0 of 2 | **2 of 2** |

  - **Applied:** `python -m app.infra.schema --database-url-env DIRECT_URL` → "Esquema aplicado en
    ep-steep-resonance-….neon.tech (DIRECT_URL)." No «PARA».
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
