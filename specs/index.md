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
  and `kb/` ingestion kept; constitution Amendment 1 — **verified** (2026-11-17; spec, plan and
  tasks verified by human; implementation N0 next):
  - [clarifications](./003-n8n-migration/clarifications.md) — scope reduction on top
  - [spec](./003-n8n-migration/spec.md) — D1–D11
  - [plan](./003-n8n-migration/plan.md) — node-by-node design
  - [tasks](./003-n8n-migration/tasks.md) — N0–N8

Pending (not yet scaffolded): SPEC-003 (urgencias), SPEC-004 (citas), and
the remaining PRD stories (US-006 to US-008) per `docs/03-prd.md` §11.
