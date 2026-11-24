---
type: tasks
spec_id: SPEC-009
title: reminders — Task Breakdown
description: Ordered, test-first tasks for reminders — read-only preflight (hosts, «Neon main», A and B as published, pgcrypto, no workflow C yet), the JS modules, 006_reminders.sql on the test branch and main, C and A through the MCP with pinned data, the daytime Telegram test, and exports and docs.
tags: [tasks, reminders, SPEC-009]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
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

- [x] N0 **[humano for the credential, only if it changed]**: Preflight, read-only (plan Step 0;
  RM32).
  - Done 2026-11-23 (20:14 UTC). Only reads were made: read-only connections to Neon, the MCP, and
    n8n's local database (metadata only). Nothing was created or changed.
  - **Neon:**

    | | `DIRECT_URL` (main) | `TEST_DATABASE_URL` |
    |---|---|---|
    | Host | `ep-steep-resonance-…` | `ep-blue-firefly-…` |
    | Branch | `br-crims…` | `br-cool-…` |
    | `pgcrypto` | 1.4 | 1.4 |
    | SPEC-004/007/008 functions | 13 of 13 | 13 of 13 |
    | SPEC-009 tables, `reminder_*` functions, `attendance_confirmed_at`, the 3 settings, the trigger | none | none |
    | Appointments | 1 `booked` (the demo one, past), 3 `cancelled` (the SPEC-008 test) | 0 |
    | `consent` / `consent_key` | 1 `accepted` / 1 | 0 / 1 |

    The hosts differ, and both are branches of the same project. No subject or key was printed.
  - **Credentials:**
    - `Neon main` (`QvG6Gru4fDSLvtzu`, postgres): `updatedAt` **22/11/2026 16:02:39 UTC**, unchanged
      since SPEC-006 K5. **The human's UI check is not needed.**
    - `Telegram LifeCenter Bot` (`VzY1vvAFNqi3JSKT`) is present; C will use it.
  - **Workflows:**
    - A (40 nodes) and B (11 nodes) are active. For both, draft = published = the export in git
      (A `7c3d4100…`, B `0b3cb06d…`).
    - A's settings are none / none / false / false, with no pinned data and no saved execution.
      B's settings are as before (saves everything, caller policy limited to A), with
      `pinData: {}` and 21 executions, the last on 23/11 19:36 UTC.
    - **No workflow C yet:** `search_workflows` finds nothing for «reminder» or «recordatorio»,
      and n8n's local database has none.
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
- [x] N1: `recordatorios.js` (new) and the `citas.js` extension, with their tests (plan Step 1;
  RM1–RM6, RM18–RM20, RM27, RM28).
  - Done 2026-11-23. Nothing was touched in n8n or Neon.
  - **Red first:**
    - `recordatorios.test.js` (new): texts, `CLINIC_ADDRESS` marked as example, `whenText` (tomorrow,
      today, later, both DST changes, a new year), `composeReminder` (no type, 4 buttons, 64
      bytes), `classifySendError`, and the sync check with C;
    - `citas.test.js`: `bk:ry`, `bk:rn`, `bk:rq` and `bk:i`; 4 `prepare` and 16 `compose` cases;
      consent required; the withdrawal line. The expected «booked» case of SPEC-007 gains the
      offer;
    - `consentimiento.test.js`: 7 cases, the reminder buttons with and without consent.
    - With only the new texts and labels in the modules: **5** checks of `recordatorios.test.js`
      and **7** of `citas.test.js` failed. `consentimiento.test.js` was already green.
      `urgencias.test.js` stayed green.
  - **Green:** the four Node tests are green.
    - The sync checks of `citas.js` (A) and `recordatorios.js` (C) are skipped «hasta N4».
      `consentimiento.js` and `urgencias.js` are still checked against the exports.
    - SPEC-007's 25/25 and 0/25 and SPEC-008's 23/23 and 0/22 are unchanged.
  - **Choices made in the code:**
    - **`consentimiento.js` does not change:** the reminder buttons are `bk:` buttons, which need
      consent by default, as the 7 new cases show.
    - The view shows the reminder line and button only when the query says whether there is a
      reminder (`has_reminder` true or false) and the appointment is at least 3 hours away.
      Otherwise it is the SPEC-008 view.
    - «Iré» answers with `ATTENDANCE_TEXT` and the «Cambiar» · «Anular» · «Hablar con recepción»
      buttons.
    - `recordatorios.js` has its own Madrid date helpers, so C carries a single module.
    - `CLINIC_ADDRESS` is «Calle de Ejemplo 1, Madrid», with `CLINIC_ADDRESS_IS_EXAMPLE = true`.
  - **Red first:** `recordatorios.test.js` and the new `citas.test.js` cases, with modules that only
    gain their texts.
  - Then the functions, until green. `consentimiento.test.js` and `urgencias.test.js` stay green.
  - The sync checks of `citas.js` and `recordatorios.js` are skipped «hasta N4».
- [x] N2 **[confirmación]**: `006_reminders.sql` on the test branch (plan Step 2; RM7–RM17, RM19,
  RM24–RM26, RM29).
  - Done 2026-11-24, after the human saw the summarized SQL, the commands and the host
    (`ep-blue-firefly-…`, the test branch, checked by a guard before running) and confirmed.
    **Main was not touched.**
  - **`tests/infra/test_reminders_sql.py`**, written first: 39 tests, fake ids `900901…`, and
    dates computed from today. Their appointments, reminders and consent rows are removed before
    and after each test, and the keys are never selected. It covers:
    - the **deferred trigger with the real SPEC-008 functions**: a move takes the reminder to the
      new appointment, a cancel deletes it, and a move into a taken slot leaves it unchanged;
    - **two claims at the same time** returning each reminder once;
    - the **consent check at sending** (revoked, or an older notice version → `skipped`);
    - **the chat id wiped in every final case** (sent, blocked, failed, skipped, stale), and a
      `CHECK` that rejects it on a final row.

    `test_g15` of SPEC-004 now expects `attendance_confirmed_at`.
  - **`app/infra/sql/006_reminders.sql`:**
    - `reminder_key`, `agenda_reminders`, `attendance_confirmed_at` and the three settings;
    - the encrypt and decrypt helpers;
    - `reminder_set` / `clear` / `state` / `forget` / `confirm`;
    - `reminder_claim_due` (one claim at a time, stale → `failed`, closed window or no consent →
      `skipped`, quiet hours, `FOR UPDATE SKIP LOCKED`) and `reminder_mark`;
    - the `DEFERRABLE INITIALLY DEFERRED` constraint trigger `agenda_reminder_follow`.

    The claim takes the consent text version as a parameter, which C will pass in N4.
  - **Red** (the reapply and file-exists tests excluded, so nothing was created): **38 failed**,
    every one because a function, table or column did not exist yet. Nothing was left on the
    test branch.
  - **Schema applied:** "Esquema aplicado en ep-blue-firefly-… (TEST_DATABASE_URL)."
  - **Two fixes in the tests, not in the SQL:**
    - the `rset` helper selected a `result` column, but the function returns a scalar;
    - with an empty chat id, the helper fell back to the patient id.

    After them, `test_reminders_sql.py` reports **39 passed**.
  - **SPEC-004 `test_g16_no_new_key_table`** failed in the full run: it allowed only
    `consent_key`. G16 is about the agenda subject, which still reuses the SPEC-006 key.
    `reminder_key` is the separate table approved in SPEC-009 Q3, so the test now expects exactly
    `consent_key` and `reminder_key`. Pointed out to the human for review.
  - **`tests/infra`:** **209 passed**.
    - One full run had an **intermittent failure of `test_g13`** (SPEC-004 NFR-07, 10 concurrent
      bookings). It passed 3 times out of 3 on its own and in the next full run. 006 does not touch
      inserts: its trigger only fires on `UPDATE` of status or `replaced_by`.
    - Its message was not captured.
  - **Afterwards** (read-only, test branch): 0 appointments, 0 reminders, `consent` 0,
    `consent_key` 1, `reminder_key` 1, 13 `reminder_*` functions, the trigger, and the settings
    24 h / 21:00 / 9:00.
  - First `tests/infra/test_reminders_sql.py`, then the SQL.
  - **Before running anything,** show the SQL, the exact commands and the host.
  - Run: red (nothing created), the schema, green, then all of `tests/infra`.
- [x] N3 **[confirmación]**: `main` (plan Step 3; RM29).
  - Done 2026-11-24, after the human saw the commands, the host (`ep-steep-resonance-…`,
    `DIRECT_URL`) and the read-only check, and confirmed. The check was first tried on the test
    branch, only to validate its queries.
  - **Before** (read-only): `kb_fragments` 9, `consent` 1, `consent_key` 1; configuration
    3/3/5/11/1/0; 4 appointments; 19 earlier public functions (the 14 agenda ones), and none of
    the 006 objects.
  - **Schema applied:** "Esquema aplicado en ep-steep-resonance-… (DIRECT_URL)."
  - **After** (read-only), every check «sí»:
    - unchanged: `kb_fragments`, `consent`, `consent_key`, the agenda configuration (except the
      three new settings), the appointments' columns up to SPEC-008, and the definition of every
      earlier function;
    - the settings are 24 h / 21:00 / 9:00, and `attendance_confirmed_at` exists and is empty;
    - `reminder_key` holds 1 row of 32 bytes (counted in the database, never read);
      `agenda_reminders` is empty;
    - the 17 new functions (13 `reminder_*`, 3 helpers, the trigger's) and the deferred
      constraint trigger `agenda_reminder_follow`.

    The digest file was deleted. No subject, key or md5 value was printed.
  - Separately, `test_g13` (SPEC-004 NFR-07) was made robust to connection failures, with the
    NFR-07 check first and never retried: 0 failures in 20 isolated runs, 2 full runs and a
    50-round stress test before the fix; 10 of 10 and 209 passed after it.
  - Show the command, the host and the read-only check, and wait.
  - Run: the check before, the schema on `DIRECT_URL`, the check after.
  - **Stop if** `kb_fragments`, `consent`, `consent_key`, the agenda configuration or the
    appointments changed.
- [x] N4: C (new) and A, with pinned data (plan Step 4; RM1–RM23, RM30).
  - Done 2026-11-24 on drafts. **Nothing was published:** A is still published at `7c3d4100…`, C
    (`SRwLvxYjPtnZwXfK`) has never been published, and **B was not touched** (`0b3cb06d…`).
  - **Human decisions before N4** (recorded in the clarifications and the spec, RM17):
    - only a 429 is retried; a 5xx, a network error or anything else becomes `failed`;
    - «Enviar recordatorio» uses `continueRegularOutput`, and «Clasificar error» decides;
    - `CONSENT_TEXT_VERSION` is in `recordatorios.js` too, checked against `consentimiento.js`.
  - **Test first:**
    - `recordatorios.test.js`: the new `classifySendError` cases (500, 502, network, other 400,
      unknown → `failed`; «4290 ms» is not a 429) and the version check. **Red: 2 checks**,
      then green. The sync check of C now also checks that the claim passes the version.
    - `test_reminders_sql.py`: `reminder_mark(…, 'failed')` wipes the chat id and is never
      claimed again, and an unknown result is rejected. **Red: 1 test**, because
      `reminder_mark` rejected `failed`.
  - **`006_reminders.sql`:** `reminder_mark` accepts `failed`. On the test branch it was applied
    by the full `pytest` run (its re-apply tests call `apply_schema`). **Not yet on `main`.**
  - **Queries tried first on the test branch** (fake ids `900971–900974`, cleaned up, then 0
    appointments, 0 reminders, 0 consent rows): `has_reminder` in «Consultar agenda»;
    «Recordatorio» (`set` twice, `confirmed`, `already`, `not_found` on an old start or another
    patient, `cleared`), which sees its own write; `had_reminder` in «Cita tras retirar»; the claim
    (0 rows in quiet hours; 1 row with the decrypted chat id; no consent → `skipped`) and the mark
    (429 → `pending` and claimed again 15 minutes later, then `sent`, `ignored`, `blocked`).
  - **Built through the MCP** from a script that generates the code from the repo files: C with
    the Workflow SDK (6 nodes), A in 5 updates (41 nodes). A CLI export showed every Code node
    identical to its module plus its wiring, the queries as tried, the connections as planned,
    the other 33 nodes of A and its settings unchanged, and C saving no execution.
  - **38 pinned runs** (A4 extension; A ids `900951–900976`, C chat ids `900981–900991`), all as
    planned:
    - **C (12):** nothing due; «mañana»; «hoy»; two at once; one returned after the other was
      skipped for consent; 403 and «chat not found» → `blocked`; 429 → `retry`; 500 and
      `ETIMEDOUT` → `failed`; a Neon failure in the claim (nothing sent) and in the mark. Every
      message has no type and 4 buttons (callbacks of at most 10 bytes), and the mark never
      carries the chat id.
    - **A (26):** the offer at 3 h or more (5 rows) and none at 2 h 59; `bk:ry` (`set`,
      `too_late`, old button); `bk:rn`; `bk:rq` (`cleared`, old button); `bk:i` (`confirmed`,
      `already`, old appointment); `/micita` with a reminder, without one, and under 3 h; a Neon
      failure in «Recordatorio» → D7; «Cambiar» and «Anular» from a reminder; without consent
      `bk:ry`, `bk:rn`, `bk:rq` and `bk:i` → the notice, and «Anular» → confirmation; the
      withdrawal with an appointment and a reminder («No te enviaré recordatorios.»), without a
      reminder, without an appointment, and with the lookup failing. B was never called.
  - **Afterwards:** `saveManualExecutions: false` in A and C, read back; no pinned data in A
    (`null`), B (`{}`) or C (`null`); B equal to its git export.
  - **Executions for the human to delete** (2026-11-23, 23:53:56–23:58:38 UTC), every execution
    after 263: **C (12):** 275–286; **A (26):** 287–312. 264–274 do not exist; there are no
    others.
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
- [x] N4b **[confirmación]**: `reminder_mark` accepting `failed` on `main` (decision of 2026-11-24).
  - Done 2026-11-24, after the human saw the commands, the host (`ep-steep-resonance-…`,
    `DIRECT_URL`) and the read-only check, and confirmed. The check was first tried on the test
    branch, read-only, only to validate its queries.
  - **Before** (read-only): `kb_fragments` 9, `consent` 1, `consent_key` 1, `reminder_key` 1;
    4 appointments, none with «Iré»; `agenda_reminders` 0; 36 public functions;
    `reminder_mark` did not accept `failed`.
  - **Schema applied:** "Esquema aplicado en ep-steep-resonance-… (DIRECT_URL)."
  - **After** (read-only), every check «sí»: `kb_fragments`, `consent`, both keys (digests, never
    read), the whole agenda configuration and every column of the appointments unchanged;
    `attendance_confirmed_at` and `agenda_reminders` still empty; the trigger and the other 35
    public functions unchanged; `reminder_mark_at` the only function changed, now accepting
    `failed`. The digest file was deleted.
- [ ] N5 **[humano]**: Publish **C, then A**, and test from Telegram (plan Step 5; RM31).
  - **2026-11-24, first part (night):**
    - The human published C (`9b8ccecd…`) and A (`eb46a1e6…`), the versions checked in N4, and
      at 01:13 Madrid booked a cleaning for Wednesday 25/11 at 16:00 with a reminder.
    - Checked read-only at 01:18 (no subject or chat id printed): 5 appointments (2 `booked`,
      3 `cancelled`), and 1 reminder `pending`, due 24/11 at 16:00, 0 attempts, with the chat
      id stored encrypted.
    - A left 4 production records (318–321, 01:14:54–01:15:34 Madrid). This is the known
      SPEC-005 limitation: n8n keeps a temporary record for about 15 minutes even though A
      saves no executions, then deletes it (as in SPEC-007 R7 and SPEC-008 M0). Checked
      read-only at 01:31: **318–321 are gone, with no data left**, and A and C have no
      execution. Nothing was deleted by hand.
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
