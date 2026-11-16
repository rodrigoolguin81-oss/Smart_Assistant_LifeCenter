---
type: tasks
spec_id: SPEC-001
title: answer-generation — Task Breakdown
description: Granular, test-first tasks derived from the plan for grounded answer generation with layered abstention.
tags: [tasks, answer-generation, SPEC-001]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-13T00:00:00Z }
verified: { by: human, at: 2026-11-16T00:00:00Z }
stale_after: null
---

# answer-generation — Tasks

Rules for every task (AGENTS.md, [plan](./plan.md) "Test environment and model usage"):

- A failing test comes before the implementation.
- Database tests use only `TEST_DATABASE_URL`.
- No test calls Gemini: tests use `FakeLanguageModel` or a stub SDK client. Only the evals (T14,
  T15) call Gemini, run by hand.

- [x] T0 — Setup:
  - Add `google-genai` and `uvicorn` to `pyproject.toml`.
  - Add the plan's configuration variables to `.env.example` (placeholders only).
  - Add an autouse fixture in `tests/conftest.py` that removes `GOOGLE_API_KEY` from the
    environment during tests.
  - Add `tests/fakes.py` with `FakeLanguageModel` (scripted replies or exceptions, records its
    calls) and an in-memory `FakeKnowledgeRepository`.

  Test: inside a test, `GOOGLE_API_KEY` is not set; `FakeLanguageModel` returns its scripted
  replies in order and records each prompt · covers: (prerequisite for every task below)
- [x] T1 — `domain/answering/messages.py` (fixed texts, the two notices marked provisional pending
  CONF-002) and the `Answer` model with its `abstention(reason)` / `llm_error()` factories.

  Test: every factory-built response has `abstained=true`, `offer_handoff=true`, `handoff_label=
  "Hablar con recepción"`, `offer_booking=false` and `citations=[]`, and its text contains no
  euro amount and no citation · covers: R14, R15, R17
- [x] T2 — `pseudonymize()`.

  Test:
  - phone (with and without the +34 prefix, with spaces), DNI, NIE and email are replaced by
    `[TELEFONO]`, `[DNI]` and `[EMAIL]`;
  - "me llamo Ana García", "mi nombre es Luis" and "a nombre de Marta Ruiz" become `[NOMBRE]`;
  - "soy alérgica a la anestesia, ¿qué me ponéis en la limpieza?" is returned unchanged;
  - a question with no identifiers is returned unchanged.

  covers: R4
- [x] T3 — `extract_citations()` and `malformed_citations()`.

  Test:
  - extracts every `[ID | vigente desde dd/mm/aaaa]` from a text;
  - the string produced by `Fragment.cita` is recognized;
  - malformed variants (missing `|`, date in another format) are not recognized as citations;
  - bracketed source references that are not valid citations (`[TAR-001]`, `[fuente: …]`) are
    reported by `malformed_citations`, so T5 can reject them;
  - `[Hablar con recepción]` is not reported.

  covers: R10 (a, b)
- [x] T4 — `figures.py`: extraction and normalization of euro amounts, times and percentages
  (plan, "Figure normalization").

  Test, equal pairs:
  - `60 €` = `60€` = `€60` = `60,00 €` = `60.00 €` = `60 euros` = `60 EUR`;
  - `1.200 €` = `1200 €`;
  - `09:00` = `9:00` = `9 h` = `9h`;
  - `20 %` = `20%` = `20 por ciento`;
  - `20,5 %` = `20.5%`.

  Test, unequal pairs:
  - `60 €` ≠ `65 €`;
  - `9:30` ≠ `9:00`;
  - `19:00` ≠ `9:00`;
  - `20 %` ≠ `25 %`;
  - `60 €` does not match `60 %` (different kind).

  Test, unvalidatable currency: "sesenta euros", "unos euros" and a bare `EUR` are reported as
  such.

  covers: R10 (c, d)
- [x] T5 — `validate_answer(text, retrieved)`.

  Test:
  - Accepted: a cited answer whose figures are in its cited fragments, including when they differ
    only in format (`60€` vs `60 €`, `09:00` vs `9:00`).
  - Rejected with the right failure kind:
    - no citation;
    - a citation with an ID or date that was not retrieved;
    - a malformed source reference (`[TAR-001]`), even next to a valid citation;
    - a euro amount absent from the cited fragments (even if another retrieved but uncited
      fragment contains it);
    - a price written in words;
    - `EUR`/`euros` without a digit amount;
    - a digit amount followed by `EUR` that is absent from the cited fragments;
    - a time (`9:30`, `9 h` when the fragment does not say 9:00) or a percentage absent from the
      cited fragments.

  covers: R10, R11
- [x] T6 — `build_prompt()`.

  Test:
  - the system prompt contains the rules: fragments only, Spanish, verbatim citations, prices in
    digits with `€`, clock times as `HH:MM`, durations with `horas`/`minutos` and never `h`, no
    clinical advice, diagnoses or medication, `answerable: false` when the
    fragments do not answer, and the patient's text treated as data;
  - the user part contains every fragment's `cita` and text, and the question inside its
    delimiters;
  - a question containing "ignora tus instrucciones" stays inside the delimiters.

  covers: R8
- [ ] T7 — `ports.py` (`LanguageModel`, `ModelReply`, `LanguageModelError` with `kind` and an
  optional `retry_after_seconds`) and `cost.py`.

  Test:
  - `estimate_cost_eur` with known token counts and prices returns the expected `Decimal`; zero
    tokens cost 0;
  - `LanguageModelError` rejects an unknown `kind`.

  covers: R16, R18
- [ ] T8 — `answer_question()`, with `FakeKnowledgeRepository` + `FakeLanguageModel`.

  Test:
  - `below_threshold` → abstention and the fake records no call;
  - `answerable: false` → abstention, and the model's text does not appear;
  - an invalid citation or figure → abstention with `reason=validation_failed`, and the fake
    records exactly one call (no retry);
  - `LanguageModelError` → LLM-error message with `reason=llm_error`;
  - a valid "¿Cuánto cuesta una limpieza?" answer over a `TAR-001` (`ejemplo: true`, `tipo:
    tarifa`) fragment → answer + price notice + example notice, `offer_booking=true`, `citations`
    filled;
  - a valid answer about the schedule (`HOR-001`) → no price notice, `offer_booking=false`;
  - the question sent to the model and to the repository is the pseudonymized one;
  - telemetry carries the latency (fake clock), tokens (0 when the model was not called) and cost.

  covers: R4–R7, R9, R11–R18
- [ ] T9 — `infra/llm_gemini.py` (`GeminiLanguageModel`) with an injected SDK client.

  Test, with a stub client and no network:
  - a valid JSON reply → `ModelReply` with the tokens taken from the usage metadata;
  - the request asks for JSON structured output with the `answerable`/`answer` schema and uses
    the configured model and timeout;
  - a timeout, an SDK exception, non-JSON output or a missing field → `LanguageModelError` with the
    matching `kind` (`timeout`, `api_error`, `invalid_output`);
  - an HTTP 429 → `kind=rate_limited`, with `retry_after_seconds` when the error provides it;
  - the adapter makes exactly one call (no retries).

  covers: R8, R16
- [ ] T10 — `infra/telemetry.py`.

  Test: the log record (captured with `caplog`) contains the pseudonymized question, `reason`,
  `error_kind` (on `llm_error`), latency, tokens and cost, and never the original
  phone/DNI/email/name · covers: R5, R18
- [ ] T11 — `POST /conversation/answer`, the token dependency, `create_app(language_model=…)` with
  its startup check, and `app/__main__.py`.

  Test:
  - Against `TEST_DATABASE_URL` with `FakeLanguageModel`:
    - no `X-Api-Token` → 401;
    - a wrong token → 401;
    - in both 401 cases, neither the fake model nor `open_repository` is invoked;
    - a wrong token **of the same length** as the real one → 401;
    - a header with non-ASCII characters → 401 (not 500);
    - the dependency compares with `hmac.compare_digest` (spied with `monkeypatch`: it is called
      once per request with the expected arguments), never with `==`;
    - a scripted `LanguageModelError(kind=rate_limited)` → 200, `reason=llm_error`, header
      `X-LLM-Error-Kind: rate_limited`, and the fake records exactly one call (the endpoint does
      not retry);
    - with the right token, after ingesting `kb/` into the test branch, "¿Cuánto cuesta una
      limpieza?" with a scripted cited reply → 200 and the response matches the contract;
    - a scripted invalid reply → 200, `abstained=true`, `offer_booking=false`.
  - `create_app` with an empty `CONVERSATION_API_TOKEN` fails at startup.
  - The entry point's default host is `127.0.0.1`.

  covers: R1, R2, R3, R17
- [ ] T12 — Extend `evals/abstention_dataset.yaml` to 50 questions:
  - remove the symptom question;
  - add a `category` field;
  - include 3–5 `injection` items and `price_trap` items;
  - include 2–3 `duration` items (durations of treatments not given in `kb/`).

  Test: the loader validates 50 entries, no duplicates, valid categories, 3–5 `injection` items,
  2–3 `duration` items and no symptom wording from a small list of keywords · covers: NFR-03 (data), Q9, Q10
- [ ] T13 — `evals/judge.py`: `Judge` port, written rubric, Gemini judge selected by
  `JUDGE_PROVIDER`/`JUDGE_MODEL`.

  The rubric has two binary criteria: `abstained`, and `figures_match_question` (each figure
  corresponds to what was asked; `null` when the answer abstained or has no figures).

  Test, with a stub client:
  - the verdict JSON is parsed into `abstained` (bool) and `figures_match_question`
    (bool or `null`);
  - the rubric text includes the attribution criterion;
  - an unknown provider fails;
  - the guard refuses to run when the judge model equals `GEMINI_MODEL`;
  - a 429 from the judge is mapped to `rate_limited` so that `RetryOnRateLimit` (T14) can retry
    it.

  covers: R19
- [ ] T14 — `evals/eval_abstention.py` per the plan: NFR-03, the injection check, the
  false-abstention counter-metric, NFR-06, NFR-02 cost, p95, the figure-attribution check, and the
  `evals/reports/` review file with ≥ 10 sampled cases. Includes the trap dataset
  `evals/attribution_dataset.yaml`: 2–3 answerable questions, each with `question`,
  `expected_id` and `expected_figures`, whose document holds other figures of the same kind.

  Also `evals/rate_limit.py::RetryOnRateLimit` (plan, "Gemini free-tier limits"), wrapping the
  generator and the judge, used only in evals and never in `create_app`.

  Test, with fakes and no Gemini, using an injected `sleep` so no real waiting happens:
  - after two `rate_limited` errors and then a reply, the reply is returned, the wrapper counts
    2 × 429, and the waits follow the server's delay or the capped exponential backoff;
  - after exhausting `EVAL_MAX_RETRIES`, the item counts as `llm_error` and is listed;
  - errors of another `kind` are not retried;
  - the report shows the number of 429s, retries, the total wait time and the discarded items,
    and its p95 excludes items that suffered a 429;
  - the report arithmetic is correct;
  - the attribution dataset loader validates 2–3 items, each with a valid `expected_id` and
    `expected_figures` parseable by `extract_figures`;
  - a trap answer "el blanqueamiento cuesta 60 € [TAR-001 | …]" (which passes R10) is flagged as
    misattributed by the deterministic check and makes the exit code ≠ 0, as does a judge verdict
    `figures_match_question: false` on a trap item;
  - a judge-flagged misattribution on the other datasets is listed in the report;
  - a non-abstained answer containing "dura 30 minutos" whose cited fragment says "45 minutos"
    is listed under "duraciones no respaldadas", without affecting the exit code;
  - the exit code is ≠ 0 when NFR-03, NFR-06 or NFR-02 is missed;
  - the review file contains ≥ 10 cases;
  - the script refuses to run when the URL equals `DATABASE_URL`/`DIRECT_URL`.

  Manual run with real Gemini: record the results and the human review in the clarifications
  (as SPEC-002 Q10 did) · covers: NFR-03, NFR-06, NFR-02, R19, R-01 (figure attribution)
- [ ] T15 — `evals/load_answer.py`: 5 concurrent requests against `python -m app
  --database-url-env TEST_DATABASE_URL`.

  Requests go in rounds of 5. When a round contains `X-LLM-Error-Kind: rate_limited`, the script
  waits with backoff and repeats the whole round.

  Test, with a mocked `httpx` transport and an injected `sleep`:
  - a round with a 429 is repeated and excluded from p95;
  - the report counts the 429s, the repeated rounds and the wait time;
  - the p95 computation and the exit code are correct.

  Manual run: p95 ≤ 5 s · covers: NFR-01
- [ ] T16 — Docs: README run instructions (`python -m app`, the n8n header and token); update
  `specs/index.md` and the PRD traceability row SPEC-001 status · test: links resolve, and the
  OKF frontmatter of every SPEC-001 artifact is valid · covers: (traceability)
