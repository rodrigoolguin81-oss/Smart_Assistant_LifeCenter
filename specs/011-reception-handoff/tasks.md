---
type: tasks
spec_id: SPEC-010
title: reception handoff, complaints and ratings — Task Breakdown
description: Ordered, test-first tasks for the reception handoff — read-only preflight, the JS modules, 007_reception.sql on the test branch and main, the group id stored by the human, A through the MCP with pinned data, the Telegram test, and exports and docs.
tags: [tasks, reception, handoff, complaints, ratings, SPEC-010]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-24T00:00:00Z }
verified: { by: human, at: 2026-11-24T00:00:00Z }
stale_after: null
---

# reception handoff, complaints and ratings — Tasks

- One task at a time, with the human's confirmation in between.
- **[confirmación]**: wait for the go-ahead before creating or changing objects in Neon or the
  workflows. Warn before anything that re-applies the schema, even on the test branch.
- **[humano]**: needs the human. Nothing is committed unless the human asks.

- [x] H0: Preflight, read-only (plan Step 0).
  - Done 2026-11-24 (about 10:40 UTC). Only reads: Neon read-only connections and n8n's local
    database (metadata only). Nothing was created or changed.
  - **Neon:** `DIRECT_URL` → `ep-steep-resonance-…` (main), `TEST_DATABASE_URL` →
    `ep-blue-firefly-…` (test); the hosts differ. On both: `pgcrypto` 1.4; 18 `agenda_*`,
    5 `consent_*` and 13 `reminder_*` functions; `agenda_reminders` and `reminder_key` present;
    **no `reception_settings`, `reception_handoffs`, `feedback_daily`, `handoff_*` or
    `feedback_*` yet**.
    - main: appointments 2 `booked` and 3 `cancelled`, 1 reminder `pending` (the SPEC-009
      test), `consent` 1, `consent_key` 1, `reminder_key` 1;
    - test: no appointments, reminders or consent rows; `consent_key` 1, `reminder_key` 1.
  - **Credentials:** `Neon main` (postgres) `updatedAt` 22/11/2026 16:02:39 UTC, unchanged since
    SPEC-006 K5, so the UI check is not needed; `Telegram LifeCenter Bot` present.
  - **Workflows:** A (`eb46a1e6…`), B (`0b3cb06d…`) and C (`9b8ccecd…`) are active, with
    draft = published = the export in git. A and C save nothing (none / none / false), B as
    before. No pinned data (A and C `null`, B `{}`).
  - **Executions:** B 21 (last 263). C had one record, 328, of its scheduled run at 10:26:56 UTC:
    the SPEC-005 transient record. Checked at 10:44 UTC: **328 is gone**. 329, of the next run at
    10:41:56, is the same case.
- [x] H1: `recepcion.js`, the `consentimiento.js` routing and the keyboard, test-first (plan
  Step 1).
  - Done 2026-11-24. Nothing was touched in n8n or Neon.
  - **Red first:** 11 checks of the new `recepcion.test.js` and 8 of `consentimiento.test.js`
    failed (17 of the 20 new `decide` cases); `citas`, `recordatorios` and `urgencias` stayed
    green. Two old expectations changed with the spec (RH1, RH2): the old `handoff` button now
    reads as a request (`reason: 'p'`), and the handoff goes through `decide` (the consent check),
    so C12's own branch is gone; a group update is the new branch that never reaches `decide`.
  - **Green:** the five Node tests. The sync checks of `recepcion.js` and `consentimiento.js` are
    skipped «hasta H4».
  - **`consentimiento.js`** (Clasificar / Decidir): `/queja`; `handoff:a|u|p|q`, `hs:<r>`, `hn`,
    `rt:u|d`; any non-private chat → a `group` route with no sender id; the strict complaint list
    (`evals/complaint_phrases.yaml`, 16 positives, 16 negatives, none of the booking or change
    phrases); `decide` for the handoff steps, `/queja`, complaint phrases and ratings, with and
    without consent, an urgency always first, and the text a handoff waits for.
  - **`recepcion.js`** (new, for «Recepción» and «Grupo de recepción»): the texts and labels,
    the reasons, the code pattern, the confirmation, the group message, the patient's texts,
    what to do with a group update (only a text reply to the bot, or «Cerrar», in the registered
    group), and the keyboard under B's replies (the reason in «Hablar con recepción», «Pedir
    cita», and 👍/👎 only under `answered`).
  - **Choice made in the code:** the complaint phrases are in `consentimiento.js` (Decidir), not
    `citas.js`, so a phrase without consent gets `COMPLAINT_NO_CONSENT_TEXT` (RH15) before the
    consent check. `citas.js` does not change: its «Hablar con recepción» buttons (`handoff`) read
    as `handoff:p`.
- [ ] H2 **[confirmación]**: `007_reception.sql` on the test branch (plan Step 2).
- [ ] H3 **[confirmación]**: `main` (plan Step 3).
- [ ] H3b **[humano]**: the group id into `reception_settings` with a hidden prompt (plan
  Step 3b).
- [ ] H4: A through the MCP, with pinned data (plan Step 4).
- [ ] H5 **[humano]**: the auto-delete timer (1 week), publish A, Telegram test (plan Step 5).
- [ ] H6: Exports and docs (plan Step 6).
