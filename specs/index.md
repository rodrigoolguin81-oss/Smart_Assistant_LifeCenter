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
  **built, pending L6** (2026-11-20; clarifications, spec, plan and tasks verified by human;
  L0–L5 and L7 done; L6 short pruning test awaiting its final check. Accepted limitation: A's
  running execution stays in n8n's local database for up to about 15 minutes):
  - [clarifications](./005-pseudonymized-log/clarifications.md)
  - [spec](./005-pseudonymized-log/spec.md) — P1–P17
  - [plan](./005-pseudonymized-log/plan.md) — Steps 0–7
  - [tasks](./005-pseudonymized-log/tasks.md) — L0–L7
  - Workflows: [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)
    (A, channel, saves nothing) and
    [`n8n/workflows/lifecenter-demo-core.json`](../n8n/workflows/lifecenter-demo-core.json) (B,
    core, executions kept 30 days) · retention: `n8n-start.ps1 -ExecutionsMaxAgeHours`

Pending (not yet scaffolded): SPEC-004 (citas), and
the remaining PRD stories (US-006 to US-008) per `docs/03-prd.md` §11.
