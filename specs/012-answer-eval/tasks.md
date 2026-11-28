---
type: tasks
spec_id: SPEC-011
title: answer quality eval — Task Breakdown
description: Ordered tasks for the answer eval — pilot, dataset and scoring test-first, the runs, and the report.
tags: [tasks, evals, SPEC-011]
status: implemented
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-28T00:00:00Z }
verified: { by: human, at: 2026-11-28T00:00:00Z }
stale_after: null
---

# answer quality eval — Tasks

One task at a time, with the human's confirmation in between. Nothing is committed unless the
human asks. No workflow, credential or Neon object changes.

- [x] E0: the 1-question pilot (plan Step 0). Execution 406 (2026-11-28): only «Recibir pregunta» pinned; «Gemini» ran for real (new `responseId`, `gemini-3.5-flash-lite`, 838 + 49 tokens); `answered`, cites TAR-001, «60 €». B unchanged at `a3682f96`.
- [x] E1: dataset and scoring, test-first (plan Step 1). `evals/answer_dataset.yaml` (73: 20 answer, 50 abstain with 11 traps, 3 urgency), `evals/eval_answers.py`, `tests/evals/test_eval_answers.py` red (no module), then 23 green.
- [x] E2: the runs through the published B (plan Step 2). Executions 408–481 (not 444, a scheduled run of C), one per item, no re-runs (0 `llm_error`); only the first gap was under 10 s (7.7 s), then a pause between runs. B at `a3682f96` with the same settings before and after.
- [x] E3: the report and the docs (plan Step 3). `evals/reports/answers-2026-11-28.md` and `.runs.json`; README and `specs/index.md` updated.
