---
type: clarifications
spec_id: SPEC-003
title: urgencies — Clarifications
description: Questions resolved with the human before writing SPEC-003 (deterministic detection of symptoms and urgencies in the n8n demo workflow, fixed reply with the clinic's urgency phone, never reaching Gemini), plus provisional clinical assumptions, limitations and the conditions that still block real patients.
tags: [clarify, urgencies, SPEC-003, US-003, RF-004, NFR-04, RES-04, CONF-003, R-02]
status: verified
sources: [../../docs/03-prd.md, ../../docs/01-charter.md, ../003-n8n-migration/spec.md, ../002-answer-generation/clarifications.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# urgencies — Clarifications

Covers PRD (`docs/03-prd.md`) US-003, RF-004, NFR-04, RES-04, CONF-003 and risk R-02, traceability
row **SPEC-003** (§11). In the n8n workflow `lifecenter-telegram-demo` (CHG-001,
`specs/003-n8n-migration/`), right after "Seudonimizar" and before "Buscar en kb", a deterministic
detector (no LLM) recognizes messages that report symptoms or urgencies. Those messages get a fixed
reply with the clinic's urgency phone, never a diagnosis or clinical advice, and **never reach
Gemini**.

Starting point: SPEC-001 assumed this upstream filter (SPEC-001 clarifications Q9) and removed
symptom questions from its abstention dataset. It also set the condition that the bot is not opened
to real patients until SPEC-003 is implemented.

## Questions & answers (human, 2026-11-19)

- Q1: One severity level or two?
  → A: **Two levels.**
  - *urgent*: any symptom gets the clinic's urgency phone.
  - *severe*: signs of a possible emergency also get the 112.

  The list of severe signs is a **provisional clinical assumption** until Prince Calderon
  validates it (see Assumptions A1).
- Q2: Fixed text, button and example phone?
  → A: **Text approved** (urgent level), with the "Hablar con recepción" button. The example phone
  is **`000 000 000`**, a number that cannot be dialed. `600 000 000` was rejected because it could
  belong to a real person. The message says the phone is an example while the real one is pending
  (DEP-01). The texts are **provisional clinical assumptions** pending Prince Calderon (A2). The
  severe-level text, the example-phone notice and the level names `severe`/`urgent` were
  approved by the human on 2026-11-19, after review of the spec.
- Q3: Where is the "configurable" phone defined?
  → A: **A constant at the top of the urgency Code node.** It is changed in one place and versioned
  in the exported workflow JSON. It is not a secret. Rejected alternatives:
  - an n8n Data Table;
  - an environment variable: n8n 2.x blocks environment access from nodes by default, and n8n
    Variables are a paid feature.
- Q4: What counts as a symptom, and what happens with doubtful cases?
  → A: **When in doubt, derive** (CONF-003 option (a)).
  - Derived: a symptom term reported as the patient's own current state (or something that
    happened after a treatment).
  - Passes to the knowledge base: informational questions about a treatment with no reported
    symptom ("¿la limpieza duele?", "¿qué cuidados hay tras la limpieza?").
  - False positives are **measured separately**. The dataset includes messages that use symptom
    words without being an urgency and must pass, such as "me duele pensar en el precio" and
    "tengo una cita el lunes".

  The term lists and the rule are **provisional clinical assumptions** (A3).
- Q5: How is the conversation "marked as urgent for reception" (US-003)?
  → A: **Only in the n8n execution**, with `reason: urgency` (and the level). The notice to
  reception (a reception chat or panel) belongs to RF-007 and is out of scope.
- Q6: Datasets and how NFR-04 is measured?
  → A: As proposed:
  - `evals/urgency_dataset.yaml` holds 30 symptom messages (some of them severe) and about 20
    normal messages that must pass.
  - The detector's source lives in `n8n/code/urgencias.js`. A Node test runs it against the
    dataset, and the Code node carries exactly that code.
  - NFR-04 is a binary eval (derived or not). "No clinical advice" holds by construction, since the
    reply is a fixed text, and the odontóloga reviews it manually.
  - There is also a live run of a sample from Telegram.
- Q7: Technical scope and location?
  → A: **n8n only**, plus the JS file and its test. No Python port: SPEC-001 T8–T16 stay paused.
  The folder is `specs/004-urgencies/` with `spec_id: SPEC-003`, following the pattern of
  `002-answer-generation` (SPEC-001).

## Assumptions

Clinical criteria are provisional until validated by Prince Calderon (odontóloga, owner of R-02 and
CONF-003). Each one is marked as such in the spec.

- **A1 — Severe signs (Q1):**
  - difficulty breathing or swallowing;
  - swelling of the face or neck that grows or closes the eye;
  - bleeding that does not stop;
  - a strong blow to the face, jaw or head (for example, with loss of consciousness or a knocked-out
    tooth after an accident);
  - high fever together with swelling.
- **A2 — Fixed texts (Q2):** all the texts are approved by the human: the urgent and severe
  messages and the example-phone notice. They are still pending clinical validation.
- **A3 — Symptom detection (Q4):**
  - Symptom terms: pain, bleeding, swelling or inflammation, fever, pus, abscess or flemón, blow or
    trauma, a broken, loose or knocked-out tooth, and a lost filling or crown.
  - These count when they are reported as the patient's state ("me duele", "tengo", "se me ha
    hinchado", "desde ayer", "después de la limpieza me sangra").
  - Figurative or non-clinical uses do not count ("me duele pensar en el precio").
  - Neither do questions about what a treatment is like ("¿la limpieza duele?").
- **A4:** detection runs on the **pseudonymized** text. Placeholders such as `[NOMBRE]` or
  `[TELEFONO]` do not affect it.
- **A5:** the patient writes in Spanish, often in lowercase, without accents and with typos. The
  detector normalizes case and accents. It does **not** correct arbitrary typos (see Known
  limitations).

## Known limitations

- **Lexical detection.** A symptom described with words outside the lists (a paraphrase, slang or
  a strong typo) is not detected. The message then follows the normal path, where the SPEC-001
  prompt forbids clinical advice and abstention remains possible. The dataset and the odontóloga's
  review are the safety net. The lists grow with each case found.
- **Over-derivation.** "When in doubt, derive" will send some harmless messages to the urgency
  reply (for example, a question about normal sensitivity after a cleaning). This is accepted by
  design (Q4) and measured as false positives.
- **Single message.** Each message is judged alone, with no conversation history (CHG-001 has no
  memory). A symptom split across two messages is judged message by message.

## Clinical review status (human, 2026-11-19)

Prince Calderon's review of the dataset, the fixed texts, the severe-sign list and the symptom
rule (A1–A3, NFR-04 manual review, U19) is **pending**. SPEC-003 is closed **for the demo only**
with this review pending. The criteria stay provisional, and opening to real patients stays
blocked (see below).

## Dependencies and conditions

- **Clinical validation (Prince Calderon):** the severe-sign list, the texts and the symptom rule
  (A1–A3), and the manual review of the dataset (NFR-04).
- **DEP-01:** the real urgency phone of the clinic. Until then the reply shows `000 000 000` and
  says it is an example.
- **RF-007:** notice to reception or the reception panel (Q5), not part of this spec.
- **Opening to real patients is still blocked** after SPEC-003, although SPEC-001's condition (Q9)
  is met. These remain:
  - n8n stores every execution with the raw Telegram message (CHG-001 D11, RES-02 and NFR-08:
    there is no 30-day purge);
  - the Gemini free tier, which may use the data and has variable latency (SPEC-001 Q1; CHG-001
    "Demo deviation from NFR-01" and "Demo model");
  - the example data in `kb/` and the example phone (DEP-01);
  - the clinical assumptions A1–A3, not yet validated;
  - the consent in the first message (CONF-005, DEP-04).
