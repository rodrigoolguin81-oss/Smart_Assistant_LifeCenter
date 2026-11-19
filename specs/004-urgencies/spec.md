---
type: spec
spec_id: SPEC-003
title: urgencies — Functional Spec
description: Requirements for deterministic detection of symptoms and urgencies in the n8n demo workflow, with a fixed two-level reply carrying the clinic's urgency phone, no clinical advice and no call to Neon or Gemini (US-003, RF-004, NFR-04, RES-04, CONF-003, R-02), in EARS notation.
tags: [spec, urgencies, SPEC-003, US-003, RF-004, NFR-04, RES-04, CONF-003, R-02]
status: implemented
sources: [./clarifications.md, ../../docs/03-prd.md, ../003-n8n-migration/spec.md, ../002-answer-generation/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# urgencies — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-003), §5.1 (RF-004), §5.2 (NFR-04), §6 (RES-04), §8
(R-02), §9 (DEP-01), §10 (CONF-003), §11 (**SPEC-003**). Extends the CHG-001 workflow
`lifecenter-telegram-demo` (`specs/003-n8n-migration/`). Decisions in
[clarifications](./clarifications.md).

## Context

Si un paciente cuenta un síntoma ("me sangra mucho la encía desde ayer"), el asistente no puede
valorarlo ni aconsejar nada (RES-04): tiene que derivarlo enseguida al teléfono de urgencias de la
clínica. Hoy el flujo de la demo enviaría ese mensaje a la búsqueda y a Gemini. Esta spec añade un
detector determinista justo después de seudonimizar. Si detecta un síntoma, responde con un texto
fijo y el flujo termina ahí. Ante la duda, deriva.

**Definitions.**

- *Symptom term*: a word or expression from the provisional lists of the plan for pain, bleeding,
  swelling or inflammation, fever, pus, abscess or flemón, blow or trauma, a broken, loose or
  knocked-out tooth, or a lost filling or crown (clarifications A3).
- *Reported symptom*: a symptom term presented as the patient's own current or recent state,
  including after a treatment, as opposed to a question about what a treatment is like or a
  figurative use.
- *Severe sign*: a reported symptom that matches the provisional severe list (clarifications A1).
- *Level*: the detector's result, one of `severe`, `urgent` or `none`.
- *Urgency phone*: the constant `URGENCY_PHONE` at the top of the urgency Code node. While the real
  number is pending (DEP-01) its value is `000 000 000` and `URGENCY_PHONE_IS_EXAMPLE` is `true`.

**Fixed texts** (provisional, pending Prince Calderon; clarifications A2):

- `URGENT_MESSAGE` (text approved by the human, 2026-11-19):
  "No puedo valorar síntomas por aquí. Llama a la clínica al {URGENCY_PHONE}. Si es grave o tienes
  dificultad para respirar, llama al 112."
- `SEVERE_MESSAGE` (approved by the human, 2026-11-19):
  "Si tienes dificultad para respirar o tragar, una hemorragia que no para o te has dado un golpe
  fuerte en la cara o la cabeza, llama ahora al 112. No puedo valorar síntomas por aquí. Si no es
  una emergencia, llama a la clínica al {URGENCY_PHONE}."
- `EXAMPLE_PHONE_NOTICE` (approved by the human, 2026-11-19), appended on a new paragraph while
  `URGENCY_PHONE_IS_EXAMPLE` is `true`:
  "(Este teléfono es de ejemplo: todavía no tenemos el número real de la clínica.)"

## Requirements (EARS)

### Placement and isolation (RF-004, R-02)

- U1. WHEN a Telegram text message arrives, the workflow SHALL run the urgency detector on the
  pseudonymized text, after "Seudonimizar" and before "Buscar en kb".
- U2. The detector SHALL be deterministic: rules over the text only, with no language model, no
  network call and no database access.
- U3. IF the level is `severe` or `urgent`, THEN the workflow SHALL NOT query Neon nor call Gemini
  for that message.
- U4. WHEN the level is `none`, the workflow SHALL continue exactly as in CHG-001 (D3–D8).

### Classification (CONF-003, clarifications Q4)

- U5. WHEN a message reports a symptom, the detector SHALL return `urgent` or `severe`. This
  includes symptoms after a treatment ("¿es normal que me sangre la encía después de la
  limpieza?").
- U6. WHEN a reported symptom matches a severe sign, the detector SHALL return `severe`.
- U7. WHEN a message only asks what a treatment is like or what its aftercare is, with no reported
  symptom ("¿la limpieza duele?", "¿qué cuidados hay después de la limpieza?"), the detector SHALL
  return `none`.
- U8. WHEN a symptom word is used figuratively or with a non-clinical meaning ("me duele pensar en
  el precio", "tengo una cita el lunes"), the detector SHALL return `none`.
- U9. IF a message cannot be placed clearly under U7 or U8, THEN the detector SHALL return
  `urgent`. When in doubt, it derives.
- U10. The detector SHALL ignore letter case and accents, and SHALL treat SPEC-001 placeholders
  (`[NOMBRE]`, `[TELEFONO]`, `[DNI]`, `[EMAIL]`) as non-symptom text.

### Reply (US-003, RES-04)

- U11. WHEN the level is `urgent`, the workflow SHALL reply with `URGENT_MESSAGE`. WHEN it is
  `severe`, it SHALL reply with `SEVERE_MESSAGE`. In both cases it SHALL add the
  `EXAMPLE_PHONE_NOTICE` while the phone is an example, and the "Hablar con recepción" button.
- U12. The reply SHALL consist only of the fixed text. It SHALL NOT include any part of the
  patient's message, any diagnosis, any clinical advice or any medication recommendation (RES-04).
- U13. The urgency phone SHALL be defined once, as a constant at the top of the urgency Code node,
  and both messages SHALL be built from it.
- U14. WHEN the patient taps "Hablar con recepción" after an urgency reply, the workflow SHALL reply
  with the CHG-001 D8 text, as for any other handoff.

### Marking for reception (US-003, clarifications Q5)

- U15. WHEN the level is `severe` or `urgent`, the execution SHALL record `reason: urgency`, the
  level and the rules or terms that matched, so the case can be identified and reviewed in n8n's
  Executions list. No notice SHALL be sent to reception (that is RF-007).

### Code and evaluation (NFR-04, clarifications Q6)

- U16. The detector's source SHALL live in `n8n/code/urgencias.js`. The urgency Code node SHALL
  carry exactly that code, plus only the n8n input and output wiring.
- U17. `evals/urgency_dataset.yaml` SHALL contain 30 messages that report symptoms, each labelled
  `urgent` or `severe` (at least 5 `severe`), and about 20 normal messages labelled `none`. The
  normal messages SHALL include treatment and aftercare questions, figurative uses of symptom words
  and ordinary messages (prices, schedules, appointments).
- U18. A Node test SHALL run the detector over the dataset and report:
  - NFR-04: the share of the 30 symptom messages derived (`urgent` or `severe`), which SHALL be
    100 %;
  - the `severe` messages classified `severe`;
  - the false positives: normal messages classified `urgent` or `severe`. They are reported
    separately and every one is listed for review.
- U19. Before SPEC-003 is marked implemented, Prince Calderon SHALL review the dataset, the fixed
  texts and the severe-sign list. Until then they remain provisional and are recorded as such.

## Acceptance criteria

- [x] The Node test passes: 30/30 symptom messages derived, every `severe` message classified
  `severe`, and the false-positive count reported with the list of messages.
- [x] From Telegram, "me sangra mucho la encía desde ayer" → `URGENT_MESSAGE` with `000 000 000`,
  the example notice and the "Hablar con recepción" button. The execution shows
  `reason: urgency`, and neither "Buscar en kb" nor "Gemini" ran.
- [x] From Telegram, "se me ha hinchado la cara y me cuesta tragar" → `SEVERE_MESSAGE` with the
  112, the example notice and the button.
- [x] From Telegram, "¿la limpieza duele?" → not an urgency. It follows the normal path (knowledge
  base and Gemini, or abstention).
- [x] From Telegram, "me duele pensar en el precio de la limpieza" and "tengo una cita el lunes" →
  not an urgency.
- [x] Tapping "Hablar con recepción" after an urgency reply → the D8 text.
- [x] The CHG-001 acceptance messages (limpieza, sábados, Sanitas, the name and phone message, the
  injection) still behave as before.
- [x] `n8n/workflows/lifecenter-telegram-demo.json` is re-exported with no secret or personal data,
  and its urgency node matches `n8n/code/urgencias.js`.
- [x] Prince Calderon's review of the dataset, the texts and the severe list is recorded, or is
  recorded as still pending (U19). Recorded as **pending** on 2026-11-19 (clarifications, "Clinical
  review status").

Checked 2026-11-19: Node test (tasks U1, U4) and Telegram executions 55, 56, 61 (urgencies) and
57–60, 62 (normal path; "la limpieza duele?" with only `?`). Still open: the button after an
urgency reply, the CHG-001 regression messages and the clinical review (U5).

Completed 2026-11-19 from Telegram:
- execution 64: "me duele mucho una muela" → `urgent`, with no "Buscar en kb" or "Gemini";
- executions 70 and 71: the button → D8 text;
- executions 65–69, the CHG-001 regression messages, all as before:
  - limpieza → 60 € with TAR-001 and both notices;
  - sábados → 10:00–14:00 with HOR-001;
  - Sanitas → `below_threshold`;
  - name and phone → `[NOMBRE]` and `[TELEFONO]` in the Gemini body, 280 €;
  - injection → `model_abstained`.

The clinical review is recorded as pending. SPEC-003 is closed **for the demo**, and opening to
real patients stays blocked.

## Out of scope

- Notice to reception, the reception panel and marking in a ticketing system (RF-007).
- Complaints (RF-009) and any other intent classification.
- A language-model classifier, and any change to the Gemini prompt.
- A Python port (SPEC-001 T8–T16 stay paused).
- Conversation memory: a symptom spread over several messages is judged message by message.
- The real urgency phone and the clinical validation themselves (DEP-01; Prince Calderon).
