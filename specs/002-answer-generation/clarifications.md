---
type: clarifications
spec_id: SPEC-001
title: answer-generation — Clarifications
description: Open questions resolved with the human before writing the SPEC-001 spec (grounded answer generation with deterministic abstention), plus assumptions, conditions and dependencies.
tags: [clarify, answer-generation, SPEC-001]
status: verified
sources: [../../docs/03-prd.md, ../001-rag-retrieval/clarifications.md]
generated: { by: claude-code, at: 2026-11-13T00:00:00Z }
verified: { by: human, at: 2026-11-13T00:00:00Z }
stale_after: null
---

# answer-generation — Clarifications

Covers PRD (`docs/03-prd.md`) RF-002, RF-003, US-001, US-002, NFR-01, NFR-02, NFR-03, NFR-06,
RES-02 and CONF-002, traceability row **SPEC-001** (§11). Given a patient's question, use the
SPEC-002 retrieval (`specs/001-rag-retrieval/`) and generate, with a language model, a Spanish
answer grounded only in the retrieved fragments with a mandatory `[ID | vigente desde dd/mm/aaaa]`
citation — or a deterministic abstention message offering a handoff to reception.

Starting point: SPEC-002 clarifications Q10 established that the lexical relevance threshold
(`0.01`) is a **recall filter, not the abstention guarantee** (it rejects only 9/19 = 47.4% of the
interim unanswerable questions). End-to-end abstention (NFR-03 ≥ 98%) is therefore this spec's
responsibility.

## Questions & answers

- Q1: Which provider and model generate the answers?
  → A: **Gemini Flash** (Google), via `GOOGLE_API_KEY`; the exact model name is configurable by
  environment variable. The provider sits behind a `LanguageModel` port in the domain so it can be
  swapped without touching the answering logic.
  **Assumption / condition (data protection):** Gemini Flash on the **free tier of Google AI
  Studio is used for development only**, with example (`ejemplo: true`) data and pseudonymized
  questions. On that tier Google may use the submitted data to improve its products, so **before
  production with real patient data it is mandatory** to move to a paid plan (whose terms exclude
  that use) or to an EU provider (e.g. Mistral), consistent with RES-02 and RES-05.

- Q2: NFR-03 requires an LLM-as-judge with "a different model". What counts as different?
  → A: **Same provider, different model** (another Gemini variant/size, configurable). The eval
  refuses to run if the judge model equals the generator model.
  **Mitigation of shared-provider bias:** the judge emits a **binary verdict** (abstained / did
  not abstain) against an **explicit written rubric**; a **manual review of a sample of ≥ 10
  cases** from each reported eval run is performed and its result recorded alongside the run; the
  judge's **provider and model are switchable by configuration** (e.g. to a different provider) if
  the manual review finds disagreement.

- Q3: How is abstention decided, given Q10 of SPEC-002 shows the threshold alone is insufficient?
  → A: **Layered.** (1) If retrieval reports `below_threshold`, abstain deterministically
  **without calling the model**. (2) Otherwise the model returns structured output including
  `answerable: false` when the fragments do not answer the question → abstain. (3) If the model's
  answer fails citation validation (Q4) → abstain. All three paths emit the same fixed message
  (Q13), distinguished only by an internal `reason`.

- Q4: How strict is citation validation before answering (NFR-06, mitigation of R-01)?
  → A: **Citation + figures.** Every non-abstained answer must contain at least one citation
  `[ID | vigente desde dd/mm/aaaa]` that is **identical** to the `cita` of a fragment actually
  retrieved for that question; any citation in the answer that does not match a retrieved
  fragment invalidates it; and **every euro amount** in the answer must appear literally in the
  text of a cited fragment. Any failure → abstention (no retry).
  **Extended at spec review (human, 2026-11-13):**
  - The prompt requires prices written in **digits with the `€` symbol**.
  - `EUR` and amounts written **in words** next to "euro"/"euros" also count as prices. If
    "euro", "euros" or "EUR" appears without a digit amount that can be validated against a cited
    fragment (e.g. "sesenta euros"), the system abstains.
  - Figure validation also covers **times** (`HH:MM` or "9 h") and **percentages**: each must
    appear literally in a cited fragment, or the system abstains. Each case gets its own tests.

- Q5: RES-02 — how are personal identifiers detected for pseudonymization?
  → A: **Regex + heuristics**, no heavy NLP dependency: regular expressions for Spanish phone
  numbers, DNI/NIE and email addresses; names through contextual patterns ("me llamo X",
  "mi nombre es X", "a nombre de X"). **"soy X" is deliberately excluded** (human, spec review
  2026-11-13): in Spanish it is usually followed by conditions or adjectives that are not names
  and that the assistant needs ("soy alérgica", "soy diabético"); a test checks that "soy alérgica
  a la anestesia" is left unchanged. Detected values are replaced by placeholders
  (`[NOMBRE]`, `[TELEFONO]`, `[DNI]`, `[EMAIL]`) **before** any call to the model API. Known
  limitation: a bare name with no contextual cue may not be detected (accepted for v1.0).

- Q6: Single turn or conversation history?
  → A: **Single turn**, stateless: question → answer. Multi-turn context is out of scope.

- Q7: What does "offer a handoff to reception" include in SPEC-001, given RF-007 (reception panel)
  is not specified yet?
  → A: **Flags + button label only.** The response carries `abstained`, `offer_handoff: true` and
  the button label "Hablar con recepción"; n8n renders the button. Recording the handoff and the
  reception panel belong to the RF-007 spec.

- Q8: Who adds the CONF-002 "from" price notice and the example-data notice?
  → A: **Deterministic code**, after validation, with fixed text: the prior-assessment notice when
  the answer contains a price; the example-data notice when any cited fragment has
  `ejemplo: true`. Not delegated to the model. **The texts of both notices are provisional,
  pending CONF-002** (decided by Prince Calderon); see Assumptions.

- Q9: Symptom questions (e.g. "Me sangran las encías…") belong to SPEC-003, and RES-02 forbids
  sending health data to the model. How does SPEC-001 treat them?
  → A: **Assume an upstream filter:** SPEC-001 assumes the SPEC-003 urgency/symptom classifier
  runs before it. Symptom questions are removed from the abstention dataset and moved to the
  future NFR-04 dataset.
  **Defense in depth:** the model's system prompt forbids clinical advice, diagnoses and
  medication recommendations (RES-04) regardless.
  **Condition:** the bot **is not opened to real patients until SPEC-003 is implemented.**

- Q10: How are the evaluation datasets extended?
  → A: Extend `evals/abstention_dataset.yaml` to **50 unanswerable questions** (removing the
  symptom one per Q9), mixing questions with and without lexical overlap with `kb/` and "price
  traps" (treatments the clinic might offer but `kb/` does not price). Include **3–5 prompt
  injection attempts** (e.g. "ignora tus instrucciones…", "invéntate un precio…", asking to cite a
  non-existent ID): each must end in abstention or in a cited answer that passes Q4 validation.
  Additionally, measure the **false-abstention rate** over `evals/retrieval_dataset.yaml` (23
  answerable questions) as a counter-metric, so NFR-03 cannot be "won" by always abstaining.

- Q11: How are NFR-01 (p95 ≤ 5 s with 5 concurrent conversations) and NFR-02 (≤ 0.01 € per
  conversation) verified within SPEC-001?
  → A: Each answer records latency, input/output tokens and estimated cost (per-token prices held
  in configuration). The abstention eval reports p95 latency and mean cost; a small script fires
  5 concurrent requests at the endpoint and reports p95. The end-to-end load test through
  n8n/Telegram is out of scope.

- Q12: What does the bot answer if the model API fails (timeout, 5xx, invalid JSON)?
  → A: A **distinct fixed message** plus the handoff offer, **no retries**, with a configurable
  timeout that fits within the 5 s latency budget. Recorded with its own `reason` so telemetry
  distinguishes "don't know" from "failed".

- Q13: Exact abstention wording?
  → A: "Lo siento, no tengo esa información. ¿Quieres que pase tu consulta a recepción?" plus the
  button "Hablar con recepción".

- Q14: US-001 says the bot "offers to book an appointment" after a price, but SPEC-004 (schedule)
  does not exist yet. What does SPEC-001 do?
  → A: Return `offer_booking: true` when a non-abstained answer cites a fragment about prices or
  treatments (`tipo` `tarifa` or `tratamiento`). n8n will show the button once SPEC-004 exists;
  there is no booking flow here. **`offer_booking` is never `true` when `abstained` is `true`**
  (human, spec review 2026-11-13).

- Q15: Folder, endpoint and exposure?
  → A: Folder `specs/002-answer-generation/` (`spec_id: SPEC-001`; folder numbers are sequential
  and independent of PRD spec IDs). Endpoint **`POST /conversation/answer`**, the one n8n calls,
  which internally uses the SPEC-002 retrieval use case.
  **Security:** the endpoint requires a **shared secret with n8n in a request header**; the token
  lives in `.env` (`CONVERSATION_API_TOKEN`, documented as a placeholder in `.env.example`) and
  never in code. A missing or wrong token → **401** without processing the question (with its
  own test). The API **listens only on localhost**; the only component exposed to the internet is
  n8n's Telegram webhook.

## Assumptions

- Development with Gemini's free tier is acceptable only under the Q1 condition (example data,
  pseudonymized questions); production requires a paid plan or an EU provider.
- A same-provider judge may share blind spots with the generator; accepted with the Q2
  mitigations (binary rubric, ≥ 10-case manual review, switchable judge).
- The SPEC-003 symptom/urgency classifier will sit upstream of this feature (Q9).
- Name detection by contextual heuristics has limited recall (Q5); the "soy X" exclusion
  trades some name recall for keeping clinically relevant context.
- Literal figure matching (Q4) can reject a correct answer that reformats a figure (e.g. `9 h` vs
  `9:00`); the false-abstention counter-metric (Q10) tracks this cost.
- Model per-token prices are maintained by hand in configuration; the cost figure is an estimate.
- **Provisional notice texts, pending CONF-002** (decided by Prince Calderon). They are proposed by
  the implementer, accepted provisionally at spec review (2026-11-13), and are to be replaced once
  CONF-002 is closed:
  - Price notice: "Los precios son «desde» y pueden variar tras una valoración previa en la
    clínica."
  - Example-data notice: "Aviso: esta información es de ejemplo y no corresponde a datos reales de
    LifeCenter."
- The relevance threshold stays at `0.01` (SPEC-002 Q10); if NFR-03 is missed end to end, that
  threshold is revisited (SPEC-002 Q10, condition 1).
- Eval datasets remain interim and hand-built over the example `kb/` until PRD DEP-01.

## Dependencies and conditions

- **SPEC-003** (urgencies/symptoms) — must be implemented before opening the bot to real patients.
- **RF-007** (handoff recording and reception panel) — consumes `offer_handoff`; not built here.
- **SPEC-004** (schedule) — consumes `offer_booking`; not built here.
- **PRD DEP-01** — real `kb/` and real question banks; datasets and threshold to be recalibrated.
- **CONF-002** — final wording of the price notice.
- **Production provider** — paid Gemini plan or EU provider before real patient data (Q1).
