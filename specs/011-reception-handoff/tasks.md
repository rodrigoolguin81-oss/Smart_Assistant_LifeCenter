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

- [ ] H0: Preflight, read-only (plan Step 0).
- [ ] H1: `recepcion.js`, the `consentimiento.js` routing and the keyboard, test-first (plan
  Step 1).
- [ ] H2 **[confirmación]**: `007_reception.sql` on the test branch (plan Step 2).
- [ ] H3 **[confirmación]**: `main` (plan Step 3).
- [ ] H3b **[humano]**: the group id into `reception_settings` with a hidden prompt (plan
  Step 3b).
- [ ] H4: A through the MCP, with pinned data (plan Step 4).
- [ ] H5 **[humano]**: the auto-delete timer (1 week), publish A, Telegram test (plan Step 5).
- [ ] H6: Exports and docs (plan Step 6).
