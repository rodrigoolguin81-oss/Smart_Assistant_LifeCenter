---
type: spec
spec_id: SPEC-001
title: answer-generation — Functional Spec
description: Functional requirements for generating grounded, cited Spanish answers from SPEC-002 retrieval with layered deterministic abstention, citation and figure validation, pseudonymization and cost/latency telemetry (RF-002, RF-003, US-001, US-002), in EARS notation.
tags: [spec, answer-generation, SPEC-001]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md, ../001-rag-retrieval/spec.md]
generated: { by: claude-code, at: 2026-11-13T00:00:00Z }
verified: { by: human, at: 2026-11-13T00:00:00Z }
stale_after: null
---

# answer-generation — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-001, US-002), §5.1 (RF-002, RF-003), §5.2 (NFR-01,
NFR-02, NFR-03, NFR-06), §6 (RES-02, RES-04), §10 (CONF-002), §11 (**SPEC-001**). Builds on
SPEC-002 (`specs/001-rag-retrieval/`).

## Context

Smart Assistant tiene que contestar preguntas frecuentes (precios, horarios, tratamientos) solo
con información oficial y citando la fuente, y decir claramente cuándo no sabe algo, sin inventar
cifras (riesgo R-01). SPEC-002 ya recupera fragmentos con su cita, pero su umbral léxico solo
filtra recall ([SPEC-002 Q10](../001-rag-retrieval/clarifications.md)). Esta feature añade la
generación de la respuesta con un modelo de lenguaje y una abstención por capas que garantiza que
toda cifra y toda cita salen de los fragmentos realmente recuperados. Decisiones en
[clarifications](./clarifications.md).

**Definitions.**
*Euro amount*: a quantity written in digits (with optional thousands/decimal separators) or in
words, immediately preceded or followed by `€` or `EUR`, or followed by the word `euro`/`euros`.
*Validatable euro amount*: a euro amount written in digits.
*Currency mention*: any occurrence of `€`, `EUR`, `euro` or `euros` in the answer text.
*Time*: a time of day written as `HH:MM`/`H:MM` (e.g. `09:30`, `9:30`) or as a number followed by
`h` (e.g. `9 h`).
*Percentage*: a number followed by `%` (with or without a space) or by the word `por ciento`.
*Figure*: a euro amount, a time or a percentage.
*Retrieved citation*: the
`cita` of a fragment returned by the SPEC-002 retrieval for the current question. *Abstention
message*: "Lo siento, no tengo esa información. ¿Quieres que pase tu consulta a recepción?".
*Handoff button label*: "Hablar con recepción".

## Requirements (EARS)

### Endpoint and access

- R1. The system SHALL expose `POST /conversation/answer`, accepting a single patient question in
  Spanish and returning one answer (single turn, stateless; no conversation history is used).
- R2. IF a request to `POST /conversation/answer` lacks the shared-secret header or its value does
  not equal the configured `CONVERSATION_API_TOKEN`, THEN the system SHALL respond `401` without
  pseudonymizing, retrieving or calling the language model. The token SHALL be read from the
  environment (`.env`) and never be hard-coded.
- R3. The application API SHALL bind to the loopback interface (`127.0.0.1`) by default; only the
  n8n Telegram webhook is exposed to the internet.

### Pseudonymization (RES-02)

- R4. WHEN a question is received, the system SHALL pseudonymize it before any further processing
  by replacing Spanish phone numbers with `[TELEFONO]`, DNI/NIE numbers with `[DNI]`, email
  addresses with `[EMAIL]`, and names introduced by "me llamo", "mi nombre es" or "a nombre de"
  with `[NOMBRE]`. The system SHALL NOT treat text following "soy" as a name, since in Spanish it
  usually introduces conditions or adjectives the assistant needs (e.g. "soy alérgica a la
  anestesia").
- R5. The system SHALL send only the pseudonymized question to the language model API and SHALL
  record only the pseudonymized question in logs and telemetry; the original text SHALL never
  leave the application.

### Retrieval and layered abstention (RF-003, US-002)

- R6. WHEN a pseudonymized question is processed, the system SHALL retrieve fragments through the
  SPEC-002 retrieval use case (top `k` = 5, configured relevance threshold).
- R7. IF retrieval reports `below_threshold`, THEN the system SHALL return the abstention message
  without calling the language model (`reason: below_threshold`).
- R8. WHEN retrieval returns fragments, the system SHALL call the language model with a system
  prompt that (a) restricts the answer to the content of the provided fragments, (b) requires
  Spanish, short sentences and the inline citation `[ID | vigente desde dd/mm/aaaa]` of every
  fragment used, (c) forbids clinical advice, diagnoses and medication recommendations (RES-04),
  (d) requires every price to be written in digits followed by the `€` symbol (never in words,
  never as `EUR`/`euros`), and (e) instructs the model to treat the patient's question as data, never as instructions; and
  SHALL request structured output containing at least `answerable` (boolean) and `answer` (text).
- R9. IF the model returns `answerable: false`, THEN the system SHALL return the abstention
  message (`reason: model_abstained`), discarding any text the model produced.

### Citation and figure validation (RF-002, NFR-06, R-01)

- R10. WHEN the model returns `answerable: true`, the system SHALL validate the answer before
  returning it: (a) it contains at least one citation in the format `[ID | vigente desde
  dd/mm/aaaa]`; (b) every citation it contains is identical to a retrieved citation; (c) every
  currency mention belongs to a validatable euro amount — a euro amount written in words, or a
  currency mention with no digit amount attached, fails validation; and (d) every figure it
  contains (validatable euro amount, time or percentage) appears literally in the text of at
  least one fragment it cites.
- R11. IF any condition of R10 fails, THEN the system SHALL return the abstention message
  (`reason: validation_failed`), without retrying the model and without returning any part of
  the model's text.

### Deterministic notices and flags (CONF-002, R7 of SPEC-002, US-001)

- R12. WHEN a validated answer contains a euro amount, the system SHALL append the fixed price
  notice "Los precios son «desde» y pueden variar tras una valoración previa en la clínica."
- R13. WHEN any fragment cited by a validated answer has `ejemplo: true`, the system SHALL append
  the fixed notice "Aviso: esta información es de ejemplo y no corresponde a datos reales de
  LifeCenter."
- The notice texts in R12 and R13 are **provisional, pending CONF-002** (decided by Prince
  Calderon); they are held as constants in one place so they can be replaced without touching the
  logic.
- R14. WHEN a validated answer cites a fragment whose `tipo` is `tarifa` or `tratamiento`, the
  system SHALL set `offer_booking: true`; otherwise `offer_booking: false`. The system SHALL NOT
  set `offer_booking: true` in any response where `abstained` is `true` (abstentions and errors
  included).
- R15. WHEN the system abstains (R7, R9, R11) or fails (R16), it SHALL set `abstained: true`,
  `offer_handoff: true` and `handoff_label: "Hablar con recepción"`, and SHALL NOT include any
  euro amount or citation in the answer text.

### Model failure (Q12)

- R16. IF the language model call times out (configurable timeout within the NFR-01 budget),
  returns an error, or returns output that does not match the structured schema, THEN the system
  SHALL return the fixed message "Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a
  recepción?" (`reason: llm_error`) without retrying.

### Response contract

- R17. The response SHALL include: `answer` (final text shown to the patient), `abstained`,
  `reason` (`answered` | `below_threshold` | `model_abstained` | `validation_failed` |
  `llm_error`), `offer_handoff`, `handoff_label`, `offer_booking`, `citations` (the validated
  citations used; empty when abstaining) and `ejemplo` (true if any cited fragment is example
  data). The response SHALL NOT depend on Telegram (RES-03).

### Telemetry (NFR-01, NFR-02)

- R18. For every answered request, the system SHALL record the end-to-end latency, the model's
  input and output tokens (zero when the model is not called), the estimated cost in euros
  computed from per-token prices held in configuration, and the `reason`.

### Evaluation (NFR-03)

- R19. The abstention eval SHALL judge each answer with an LLM-as-judge whose model differs from
  the generator model (configurable provider and model; the eval refuses to run if they are
  equal), using a binary verdict and an explicit written rubric.

## Acceptance criteria

- [ ] Given a request without the shared-secret header, or with a wrong value, the endpoint
  returns `401` and neither retrieval nor the model is invoked.
- [ ] Given a question containing a phone number, a DNI/NIE, an email and "me llamo Ana García",
  the text sent to the model contains `[TELEFONO]`, `[DNI]`, `[EMAIL]` and `[NOMBRE]` and none of
  the original values (unit test; RES-02).
- [ ] Given the question "soy alérgica a la anestesia, ¿qué me ponéis en la limpieza?", the
  pseudonymized text is identical to the original (no `[NOMBRE]` substitution).
- [ ] Given a question for which retrieval reports `below_threshold`, the abstention message is
  returned and the model is not called.
- [ ] Given the model returns `answerable: false`, the abstention message is returned.
- [ ] Given a model answer citing an ID or date not among the retrieved citations, a model answer
  without any citation, or a model answer with a euro amount absent from its cited fragments, the
  abstention message is returned with `reason: validation_failed` (deterministic tests with a
  stubbed model; NFR-06).
- [ ] Given a model answer with a price written in words ("sesenta euros"), with `EUR`/`euros`
  and no digit amount, or with a digit amount followed by `EUR` that is absent from its cited
  fragments, the abstention message is returned with `reason: validation_failed`.
- [ ] Given a model answer with a time (`09:30`, `9 h`) or a percentage (`20 %`) that does not
  appear literally in any cited fragment, the abstention message is returned with
  `reason: validation_failed`; given the same figures present literally in a cited fragment, the
  answer is accepted.
- [ ] Given any response with `abstained: true` (every `reason` other than `answered`),
  `offer_booking` is `false`.
- [ ] Given a validated answer about "¿Cuánto cuesta una limpieza?" over the example `kb/`, the
  answer cites `[TAR-001 | vigente desde 01/01/2026]` (or another retrieved citation containing
  60 €), ends with the price notice and the example-data notice, and has `offer_booking: true`.
- [ ] Given a model timeout, error or malformed output, the fixed error message is returned with
  `offer_handoff: true` and `reason: llm_error`.
- [ ] Given any abstention or error, the answer text contains no euro amount and no citation.
- [ ] **NFR-06:** in the abstention and retrieval eval runs, 100% of non-abstained answers that
  contain a euro amount carry at least one valid retrieved citation.
- [ ] **NFR-03:** over `evals/abstention_dataset.yaml` extended to 50 unanswerable questions
  (without symptom questions, including 3–5 prompt-injection attempts), the system abstains in
  ≥ 98% of cases according to the judge; every prompt-injection item ends in abstention or in a
  cited answer that passes R10.
- [ ] **Counter-metric:** over `evals/retrieval_dataset.yaml` (answerable questions), the
  false-abstention rate is reported alongside NFR-03.
- [ ] **Judge review:** each reported NFR-03 run includes a manual review of ≥ 10 judged cases with
  its result recorded.
- [ ] **NFR-01:** with 5 concurrent requests to `POST /conversation/answer`, p95 latency ≤ 5 s
  (application endpoint only; the n8n/Telegram end-to-end test is out of scope).
- [ ] **NFR-02:** the mean estimated cost per answer over the eval runs is ≤ 0.01 €.

## Out of scope

- Symptom and urgency detection (SPEC-003, RF-004) — assumed upstream; the bot is not opened to
  real patients until SPEC-003 is implemented ([clarifications](./clarifications.md) Q9).
- Complaints (RF-009).
- Multi-turn conversation and history.
- Recording handoffs and the reception panel (RF-007); booking flow (SPEC-004, RF-005).
- Conversation log storage and 30-day purge (US-007, NFR-08).
- End-to-end load test through n8n/Telegram.
- Recalibrating the threshold and datasets with real data (pending PRD DEP-01).
- Final wording of the R12/R13 notices — provisional until CONF-002 is decided by Prince Calderon.
- Production model provider choice (paid Gemini plan or EU provider) — a precondition for real
  patient data, not part of this spec ([clarifications](./clarifications.md) Q1).
