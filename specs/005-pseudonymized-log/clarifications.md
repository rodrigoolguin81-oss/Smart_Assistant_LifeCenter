---
type: clarifications
spec_id: SPEC-005
title: pseudonymized-log — Clarifications
description: Questions resolved with the human before writing SPEC-005 (pseudonymized execution history and 30-day deletion in the n8n demo), plus the facts found, assumptions, known limitations and dependencies.
tags: [clarify, pseudonymized-log, SPEC-005, US-007, NFR-08, RES-02, R-06]
status: verified
sources: [../../docs/03-prd.md, ../003-n8n-migration/clarifications.md, ../003-n8n-migration/spec.md, ../004-urgencies/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# pseudonymized-log — Clarifications

Covers PRD (`docs/03-prd.md`) US-007 and NFR-08, with RES-02, risk R-06 and DEP-04. NFR-08 has no
SPEC row in §11 yet ("Por escribir"); this feature takes **SPEC-005**, because SPEC-004 is reserved
for appointments.

Problem: CHG-001 D11 keeps n8n's full execution history so the demo can show each message's path.
That history stores the patient's original message and Telegram's personal data, and no retention
period is set. **This spec supersedes CHG-001 D11.**

## Facts found before asking (agent, 2026-11-19)

- **Where personal data appears today.** In the executions of `lifecenter-telegram-demo`:
  - the original message, in the "Telegram Trigger" and "¿Qué ha llegado?" output;
  - the Telegram profile name and username (`first_name`, `username`) and the chat id, in the
    Telegram API response saved by "Responder", "Responder con botón", "Pedir texto" and
    "Responder recepción" (seen in executions 33, 50 and 70);
  - the `chatId` in every node after "Seudonimizar".

  With a single workflow, the raw message is stored on entry and the profile name on reply.
- **n8n's pruning defaults.** Since n8n 1.0, execution pruning is on by default with a 14-day
  maximum age (336 h). `n8n-start.ps1` does not set it. **Confirmed in task L0:** the instance
  prunes with the 2.48.4 defaults, 14 days, so stored data was not kept forever. The retention
  period was not set explicitly to 30 days.
- **The "redaction" feature of n8n 2.x** (`redaction` in the execution metadata) was not used: it
  is not yet known whether it avoids storing data or only hides it in the UI.

## Questions & answers (human, 2026-11-19)

- Q1: Architecture?
  → A: **Two workflows.**
  - **A** receives from Telegram, pseudonymizes and replies, and **saves no executions**.
  - **B** holds the urgency detector, retrieval, Gemini and validation, receives only
    pseudonymized text, and **saves its executions**. The demo shows each message's path there.

  Rejected: a single workflow with n8n's redaction (its storage behaviour is unknown), and no
  executions at all plus a Neon log (it loses the path in n8n).
- Q2: What counts as personal data, and what does B receive?
  → A: The NFR-08 list (name, phone, DNI) is **extended** with:
  - **email**;
  - **Telegram data**: profile name, username, user id and chat id.

  **B receives only the pseudonymized text, with no identifier.** The flow has no memory and A
  sends the reply, so B needs no chat id. A keyed hash to group a conversation's messages was
  rejected: its secret would have nowhere safe to live, since Code nodes cannot read credentials
  and the exported JSON is public.
- Q3: Who sends the reply?
  → A: **A.** The Telegram API response, which carries the profile name, is therefore never
  stored. Accepted consequence for the demo: B's executions show the composed reply, but not the
  sending, nor the "Hablar con recepción" button, which A handles entirely.
- Q4: A's failed executions?
  → A: **Not saved**, like its successful ones. A failure in A leaves no trace beyond n8n's
  console log. B's failures are saved, since they are already pseudonymized.
- Q5: 30-day deletion, and how is it verified?
  → A: `EXECUTIONS_DATA_PRUNE=true` and `EXECUTIONS_DATA_MAX_AGE=720` (hours) in
  `n8n-start.ps1`, for the **whole instance**, including any other workflow on it. The other
  pruning settings keep n8n's defaults.

  **Note (human, 2026-11-19, after task L0):** the instance was pruning at n8n's 14-day default,
  so 720 h, the PRD's 30 days, **extends** retention compared with the default. LifeCenter's
  management (DEP-04) may decide to shorten it. The value is a single parameter of
  `n8n-start.ps1`.

  Verification is option (a): check the configuration, and run a **short test**. Start n8n once
  with `EXECUTIONS_DATA_MAX_AGE=1`, watch old test executions get deleted, then go back to 720.
- Q6: A pseudonymized log of our own in Neon?
  → A: **Not now.** B's executions, kept 30 days, cover US-007's audit. A Neon table (date,
  `reason`, level, citations, latency, with or without the pseudonymized text) plus a daily purge
  remains **an option for RF-008** (feedback from reception).
- Q7: The history stored so far, with raw messages, profile name, username and test phones?
  → A: **The human deletes all of it from the editor**, but only **after the new scheme is
  published and tested**. The task that does it carries a reminder. The MCP has no tool to delete
  executions, and the test evidence of CHG-001 and SPEC-003 is already recorded in their
  `tasks.md`.
- Q8: What pseudonymization does not cover?
  → A: **Accepted as a known limitation for the demo**, with 30-day deletion and test messages
  from the team only. The decision of substance stays with **DEP-04** (LifeCenter's management).
  See Known limitations.
- Q9: Location?
  → A: `specs/005-pseudonymized-log/` with `spec_id: SPEC-005`. The CHG-001 clarifications record
  that this spec supersedes D11.

## Assumptions

- **A1:** pseudonymization stays exactly as in SPEC-001 R4 and CHG-001 D2 (JavaScript port). This
  spec changes **where** data is stored, not how it is pseudonymized.
- **A2:** pruning is approximate. n8n deletes in periodic passes, with a short buffer before hard
  deletion, so data lives "30 days plus at most one pruning cycle". This is accepted as meeting
  NFR-08's "se purgan a los 30 días".
- **A3:** A's and B's manual test runs use synthetic data (pinned data). A saves no executions of
  any kind, manual ones included. Its logic is checked through B's executions, the Telegram tests
  and the exported configuration.
- **A4 — Approved exception (human, 2026-11-19, plan Step 2):** A's manual executions are saved
  for **one** test run with **synthetic** pinned data only. The run is reviewed, and the setting
  goes back to "not saved" **before anything is published**. That execution contains no personal
  data and is deleted with the old history (task L5).
  - **Extension for SPEC-006 (approved by the human, 2026-11-22; SPEC-006 plan Step 4, task
    K4):**
    - `saveManualExecutions` may be on in A while the SPEC-006 pinned runs are made;
    - the runs use **synthetic** updates only, with fake ids `900001…`;
    - there is **one run per scenario**;
    - the setting goes back to "not saved" right after those runs, before anything is
      published, and is read back;
    - the human deletes those executions of A, and the B executions they create, from the
      editor.

## Known limitations

- **Names without an introduction.** Pseudonymization only detects a name after "me llamo", "mi
  nombre es" or "a nombre de" (SPEC-001 Q5). A name written any other way stays in B's stored
  text.
- **Health data.** Symptoms ("me sangra la encía") are health data, a special category under the
  GDPR, even with no identifier attached. B stores them, because the demo must show the urgency
  path. They are kept 30 days.
- **Outside n8n's executions:**
  - Telegram keeps the chat on its side;
  - n8n's console and log files are not covered (the default `info` level does not log message
    content);
  - nor are backups of n8n's own database.
- **Grouping.** With no identifier in B, its executions cannot be grouped by conversation.
- **A's execution is kept briefly in n8n's local database** (found in task L6, accepted by the
  human on 2026-11-20 for the demo).
  - With "save no executions", n8n still writes A's execution, with its full data, to its local
    database (`~/.n8n/database.sqlite`) while it runs. On finishing it marks the execution
    soft-deleted.
  - The next hard-delete pass, every 15 min, removes it. Until then (**up to about 15 minutes**)
    it holds the raw message, the chat id and the Telegram profile name and username.
  - It is never shown in the editor or through the MCP, and it is not reachable from outside.
  - Execution 97 was seen soft-deleted at 18:38 UTC and gone at 18:51 UTC (L6).
  - Removing it depends on n8n's pruning being on (`EXECUTIONS_DATA_PRUNE=true`, set by
    `n8n-start.ps1`).

## Dependencies and conditions

- **DEP-04:** LifeCenter's management validates the consent, pseudonymization and retention
  policy. The 30 days and the accepted limitations are provisional until then.
- **Opening to real patients stays blocked** (SPEC-003 clarifications, "Dependencies and
  conditions"). This spec resolves the storage of raw messages (CHG-001 D11) and the missing
  purge (NFR-08). These remain open:
  - the Gemini free tier;
  - the example data and phone (DEP-01);
  - the clinical review (SPEC-003 U5);
  - consent (CONF-005);
  - **the raw data A leaves in n8n's local database for up to about 15 minutes** (Known
    limitations), which LifeCenter's management must accept or have mitigated;
  - DEP-04.
