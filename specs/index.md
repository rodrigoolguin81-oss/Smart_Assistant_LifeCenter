---
type: index
title: Smart Assistant - LifeCenter — Specs Index
description: Index of all SDD artifacts (constitution and per-feature spec/plan/tasks folders).
tags: [index, sdd]
status: draft
sources: []
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: null }
stale_after: null
---

# Specs Index

- [constitution](./constitution.md) — project-wide principles, constraints and conventions.
- **001-rag-retrieval** — knowledge base indexing and lexical retrieval (PRD `RF-001`, `RF-002`,
  traceability row **SPEC-002**) — **implemented** (2026-11-12; tasks T0–T11 done, R1–R11):
  - [clarifications](./001-rag-retrieval/clarifications.md) — includes the relevance threshold
    decision (Q10) and known limitations (vocabulary mismatch)
  - [spec](./001-rag-retrieval/spec.md)
  - [plan](./001-rag-retrieval/plan.md)
  - [tasks](./001-rag-retrieval/tasks.md)
  - Code: `app/` · tests: `tests/` · evals: `evals/` (`eval_retrieval` Recall@5 = 91.3% on the
    interim dataset; `abstention_dataset.yaml` kept for SPEC-001's NFR-03 eval)
  - Open follow-ups: recalibrate retrieval (eval + threshold) with real data once PRD DEP-01 is
    delivered; revisit the threshold if SPEC-001 misses NFR-03 end to end.

- **002-answer-generation** — grounded answer generation with layered deterministic abstention,
  citation + figure validation and pseudonymization (PRD `RF-002`, `RF-003`, `US-001`, `US-002`,
  `NFR-03`, `NFR-06`, `RES-02`, traceability row **SPEC-001**) — **specified** (2026-11-13; spec
  verified by human; plan and tasks verified 2026-11-16; Python T0–T7 done at `946162b`; T8–T16
  paused while the n8n demo (CHG-001) is built, which ports T2, T5 and T6 logic):
  - [clarifications](./002-answer-generation/clarifications.md) — Q1–Q15, including the Gemini
    free-tier condition (dev only) and the SPEC-003 precondition for real patients
  - [spec](./002-answer-generation/spec.md)
  - [plan](./002-answer-generation/plan.md) — includes the figure normalization rule
  - [tasks](./002-answer-generation/tasks.md) — T0–T16

- **003-n8n-migration** — change **CHG-001**, reduced to a **demo MVP**: one n8n workflow
  (Telegram → pseudonymize → Neon FTS → threshold → Gemini → validation → Telegram); Python code
  and `kb/` ingestion kept; constitution Amendment 1 — **implemented** (2026-11-19; N0–N8 done, all
  acceptance criteria met from Telegram). Demo
  deviations: Gemini timeout 20 s (NFR-01 not met) and model alias `gemini-flash-lite-latest` on
  the free tier:
  - [clarifications](./003-n8n-migration/clarifications.md) — scope reduction on top
  - [spec](./003-n8n-migration/spec.md) — D1–D12
  - [plan](./003-n8n-migration/plan.md) — node-by-node design
  - [tasks](./003-n8n-migration/tasks.md) — N0–N8
  - Workflow: [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)
    · how to run it: README, "Demo (n8n + Telegram)"

- **004-urgencies** — deterministic symptom/urgency detection in the n8n demo workflow, fixed
  two-level reply with the clinic's urgency phone, never reaching Gemini (PRD `US-003`, `RF-004`,
  `NFR-04`, `RES-04`, `CONF-003`, `R-02`, traceability row **SPEC-003**) — **implemented for
  the demo** (2026-11-19; U0–U5 done; NFR-04 30/30 on the dataset with 0 false positives; every
  acceptance criterion met from Telegram. The clinical review by Prince Calderon is **pending**:
  the criteria stay provisional and opening to real patients stays blocked. Example phone
  `000 000 000` until DEP-01):
  - [clarifications](./004-urgencies/clarifications.md)
  - [spec](./004-urgencies/spec.md) — U1–U19
  - [plan](./004-urgencies/plan.md) — normalization, rules, test and workflow wiring
  - [tasks](./004-urgencies/tasks.md) — U0–U5
  - Code: [`n8n/code/urgencias.js`](../n8n/code/urgencias.js) · test
    `node n8n/code/urgencias.test.js` · dataset
    [`evals/urgency_dataset.yaml`](../evals/urgency_dataset.yaml)

- **005-pseudonymized-log** — split the n8n demo into a channel workflow that stores nothing and
  a core workflow with pseudonymized executions only, deleted after 30 days (PRD `US-007`,
  `NFR-08`, `RES-02`, `R-06`; new traceability row **SPEC-005**; supersedes CHG-001 D11) —
  **implemented for the demo** (2026-11-20; L0–L7 done; 7 of 8 acceptance criteria met. L6 was
  closed by checking the configuration only: the short test never ran because port 5678 was
  already in use, so the **real deletion test is pending**. `n8n-start.ps1` now refuses to start
  when the port is in use. Accepted limitation: A's running execution stays in n8n's local
  database for up to about 15 minutes, which blocks real patients until DEP-04):
  - [clarifications](./005-pseudonymized-log/clarifications.md)
  - [spec](./005-pseudonymized-log/spec.md) — P1–P17
  - [plan](./005-pseudonymized-log/plan.md) — Steps 0–7
  - [tasks](./005-pseudonymized-log/tasks.md) — L0–L7
  - Workflows: [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)
    (A, channel, saves nothing) and
    [`n8n/workflows/lifecenter-demo-core.json`](../n8n/workflows/lifecenter-demo-core.json) (B,
    core, executions kept 30 days) · retention: `n8n-start.ps1 -ExecutionsMaxAgeHours`

- **006-consent** — explicit consent in the bot's first message in the n8n demo: notice with
  «Acepto» / «No acepto», `/privacidad` and withdrawal, urgencies always answered (detected in A),
  no call to B before consent, and a minimal consent record in Neon keyed by an HMAC of the
  Telegram `from.id` (PRD `CONF-005`, `R-06`, `DEP-04`, `RES-02`, `RF-004`; new traceability row
  **SPEC-006**; RF-006 reminders will reuse it) — **implemented for the demo** (2026-11-22; K0–K6
  done; every acceptance criterion met, by Node and SQL tests, 17 pinned runs and the Telegram
  test). Found and fixed in K5: the `Neon main` credential pointed to the test branch; it now
  points to `main`, and AGENTS.md requires checking each credential's host. Accepted
  limitations: the HMAC key is in the same database as the records, and must never be
  regenerated. Still provisional until DEP-04, so real patients stay blocked:
  - [clarifications](./006-consent/clarifications.md)
  - [spec](./006-consent/spec.md) — C1–C27
  - [plan](./006-consent/plan.md) — Steps 0–6
  - [tasks](./006-consent/tasks.md) — K0–K6
  - Code: [`n8n/code/consentimiento.js`](../n8n/code/consentimiento.js) · test
    `node n8n/code/consentimiento.test.js` · SQL
    [`app/infra/sql/002_consent.sql`](../app/infra/sql/002_consent.sql), tested by
    `tests/infra/test_consent_sql.py` (test branch only)
  - Workflow: A, [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)

- **007-agenda** — the project's own appointment agenda in Neon (RES-01). It holds opening hours,
  professionals with roles (dentist / hygienist), rooms and appointment types. It has a free-slot
  lookup and a booking primitive that never double-books (NFR-07, R-05), at most 1 future
  appointment per patient, and a pseudonymous subject (SPEC-006 key, `agenda:` prefix) kept 30
  days. There is no patient-facing flow and no n8n change. PRD `RF-005` (agenda base), `NFR-07`,
  `R-05`, `CONF-001` (option a), `DEP-03`; traceability row **SPEC-004**. Status:
  **implemented** (2026-11-22; E0–E4 done; all 14 acceptance criteria met, with 58 SQL tests on
  the test branch including NFR-07, then applied to `main` with `kb_fragments`, `consent` and the
  key unchanged). **Nothing patient-facing yet**: no n8n workflow calls it; booking, moving and
  cancelling, and reminders are later specs. Example data until DEP-01 and DEP-03:
  - [clarifications](./007-agenda/clarifications.md) — Q1–Q14
  - [spec](./007-agenda/spec.md) — G1–G23
  - [plan](./007-agenda/plan.md) — Steps 0–4 (public functions use `now()`; internal `_at`
    versions for the tests)
  - [tasks](./007-agenda/tasks.md) — E0–E4
  - Code: [`app/infra/sql/003_agenda.sql`](../app/infra/sql/003_agenda.sql) · tests
    `tests/infra/test_agenda_sql.py` (test branch only) · README, "Agenda (SPEC-004)"

- **008-booking**: booking an appointment from Telegram on the SPEC-004 agenda. PRD `US-004`,
  `RF-005` (create), `NFR-07`, `R-05`, `CONF-001` (a), and SPEC-001 R14 (`offer_booking`);
  traceability row **SPEC-007**, a follow-up of SPEC-004.
  - **Ways in:** `/cita`, a «Pedir cita» button after price or treatment answers, and strict
    booking phrases.
  - **Flow:** type menu, up to 3 slot buttons, an explicit confirmation, a message for every
    result, and `/micita`.
  - **Where it runs:** in flow A and Neon only, never through B or Gemini, with consent required.
    B only gains `offer_booking`.
  - **Status: specified** (2026-11-22; clarifications, spec, plan and tasks verified by human; R0–R7
    pending).
  - [clarifications](./008-booking/clarifications.md), Q1–Q15
  - [spec](./008-booking/spec.md), BK1–BK27
  - [plan](./008-booking/plan.md) — Steps 0–7
  - [tasks](./008-booking/tasks.md) — R0–R7

Pending (not yet scaffolded): moving and cancelling, and reminders, which are follow-ups of
SPEC-004 (proposed SPEC-008 and SPEC-009); and
the remaining PRD stories (US-006 to US-008) per `docs/03-prd.md` §11.
