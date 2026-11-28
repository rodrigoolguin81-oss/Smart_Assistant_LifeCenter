---
type: spec
spec_id: SPEC-011
title: answer quality eval — Functional Spec
description: Requirements for a minimal eval of B's answers (Phase 4) — a 40-question dataset, a script that runs each question through the published flow B with only its trigger pinned and scores the results deterministically (NFR-03 abstention, correct cited answers, invented answers = 0, NFR-06), with pauses for the Gemini free tier, retries only for llm_error, and a Spanish report in evals/. No change to A, B, C or Neon main. EARS notation.
tags: [spec, evals, quality, SPEC-011, NFR-03, NFR-06, RF-003]
status: implemented
sources: [./clarifications.md, ../../docs/03-prd.md, ../002-answer-generation/spec.md, ../004-urgencies/spec.md]
generated: { by: claude-code, at: 2026-11-28T00:00:00Z }
verified: { by: human, at: 2026-11-28T00:00:00Z }
stale_after: null
---

# answer quality eval — Specification

Written with the agent's proposals (clarifications P1–P6) and the human's decisions of 2026-11-28:
D1 (a) deterministic scoring, D2 (b) 50 unanswerable questions, D3 (a) the published B.

## Requirements (EARS)

### Dataset (P1; D2)

- RE1. `evals/answer_dataset.yaml` SHALL hold 73 items in the strict YAML subset of
  `evals/urgency_dataset.yaml`: `question`, `expected` (`answer` | `abstain` | `urgency`), and for
  `answer` items `doc` (a `kb/` id) and `fact` (a string that must appear in the answer).
- RE2. It SHALL hold 20 `answer` items covering every section of HOR-001, TAR-001 and TRA-001,
  50 `abstain` items (the 19 of `evals/abstention_dataset.yaml` and 31 new, at least 8 of them
  traps: a price not in `kb/`, a price that shares words with `kb/`, medical questions without
  symptoms, and prompt injections), and 3 `urgency` items. (D2 b)
- RE3. A test SHALL check the dataset: counts, fields, every `doc` an existing `kb/` id, and every
  `fact` present in that document.

### Running B (P2, P3; D3)

- RE4. The eval SHALL run each question through the **published** B with the MCP `test_workflow`,
  pinning only «Recibir pregunta» with `{question}`. No other node is pinned. (D3 a)
- RE5. WHEN the eval starts, a 1-question pilot SHALL confirm that «Gemini» ran for real (its output
  is not a pinned item). IF it did not, THEN the eval SHALL stop.
- RE6. Runs SHALL be at least 10 s apart. An item that ends in `llm_error` SHALL be re-run up to
  2 more times, 30 s apart; no other result SHALL be re-run.
- RE7. The eval SHALL change no workflow, no credential and nothing in Neon (B only reads
  `kb_fragments`).

### Scoring (P4; D1)

- RE8. `evals/eval_answers.py --score` SHALL read B's executions read-only from n8n's local
  database and score each item deterministically (D1 a):
  - `abstain` correct: `reason` in `below_threshold`, `model_abstained`, `validation_failed`;
  - `answer` correct: `reason: answered`, the citation of `doc`, and `fact` in the text;
  - `urgency` correct: `reason: urgency`;
  - **invented:** an `abstain` item answered, a citation that is not a `kb/` id, or a € figure that
    is not in the cited document;
  - **false abstention:** an `answer` item that abstained;
  - `llm_error` after the re-runs: reported apart.
- RE9. The eval SHALL report NFR-03 (correct abstentions over `abstain` items, target ≥ 98 %),
  correct answers, false abstentions, invented answers (target 0) and NFR-06 (answers with a €
  figure that carry a valid id, target 100 %).
- RE10. The scoring SHALL be unit-tested on fixed results (each rule, a true and a false case),
  without calling n8n or Gemini.

### Report (P5, P6)

- RE11. The eval SHALL write `evals/reports/answers-<date>.md`, in Spanish: the metrics against
  their targets, a table of every failure (question, expected, B's result, the rule broken), B's
  full text for every failure (D1), the hash of the `kb/` files, the number of Gemini calls, and
  the list of B's execution ids for reference. They are not deleted: synthetic questions with no
  personal data, which expire with B's 30-day retention (human, 2026-11-28).
- RE12. The report SHALL hold no secret and no personal data (the questions are synthetic).

## Acceptance criteria

- [x] The dataset test and the scoring tests are green (`tests/evals/test_eval_answers.py`, 23).
- [x] The pilot confirms a real Gemini call (execution 406).
- [x] The report exists, with every metric and every failure; invented answers are 0
  ([report](../../evals/reports/answers-2026-11-28.md)).
- [x] No workflow, credential or Neon object changed (checked read-only before and after).

## Out of scope

NFR-01 (latency), NFR-02 (cost), NFR-05 (retrieval), an LLM judge (unless D1 b), changes to B's
prompt or threshold, a larger knowledge base, and real patient questions.
