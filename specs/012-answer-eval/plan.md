---
type: plan
spec_id: SPEC-011
title: answer quality eval — Technical Plan
description: How to run the answer eval — a 1-question pilot through the published B with only its trigger pinned, the 73-item dataset and the scoring test-first, the runs through the MCP 10 s apart with re-runs only for llm_error, the read-only scoring from n8n's local database, and the Spanish report. Nothing in A, B, C or Neon changes.
tags: [plan, evals, SPEC-011, NFR-03]
status: verified
sources: [./spec.md, ./clarifications.md]
generated: { by: claude-code, at: 2026-11-28T00:00:00Z }
verified: { by: human, at: 2026-11-28T00:00:00Z }
stale_after: null
---

# answer quality eval — Plan

- **Step 0, pilot (RE5):** one `answer` question («¿cuánto cuesta una limpieza?») through
  `test_workflow` on the published B, pinning only «Recibir pregunta». Read the execution
  read-only: «Gemini» must have run for real (not a pinned item), with `reason` and text. Also check,
  read-only, that B is still published at the same version and that its settings are unchanged.
- **Step 1, dataset and scoring test-first (RE1–RE3, RE8–RE10):** `evals/answer_dataset.yaml`
  (73 items) and `evals/eval_answers.py` (`--plan`, `--score`), with
  `tests/evals/test_eval_answers.py` red first: the dataset shape, every `doc` and `fact` in `kb/`,
  and each scoring rule on fixed results. No n8n or Gemini in the tests.
- **Step 2, the runs (RE4, RE6, RE7):** the agent sends each item through the MCP, at least 10 s
  apart, recording the execution ids in `evals/reports/answers-<date>.runs.json`. `llm_error`
  items are re-run up to 2 more times, 30 s apart. Before and after, a read-only check: A, B and C
  at the same published version, no new object in Neon.
- **Step 3, report (RE11, RE12):** `--score` writes `evals/reports/answers-<date>.md`. Scan it for
  secrets and personal data, update the README and `specs/index.md`, and mark spec, plan and tasks
  implemented.
