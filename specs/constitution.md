---
type: constitution
title: Smart Assistant - LifeCenter — Project Constitution
description: Non-negotiable principles, constraints and conventions for this project.
tags: [governance, sdd]
status: draft
sources: []
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: null }
stale_after: null
---

# Smart Assistant - LifeCenter — Constitution

## Principles
- Spec-first: no application code is written before its spec, plan and tasks exist.
- Clarify-first: ambiguities are resolved with the human before specifying.
- Test-Driven: every task ships with a failing test first.
- Clean boundaries: domain logic stays independent of frameworks, ORM and I/O.
- Clinical safety first: the assistant never gives clinical advice, diagnoses, or medication
  recommendations; any symptom or urgency is escalated to reception without comment.
- No hallucination: every answer about prices, schedules or treatment instructions must be
  grounded in the knowledge base and cite its source document and validity date.

## Constraints
- Stack: Python (FastAPI) for the application API; python-dotenv / pydantic-settings for
  configuration; n8n as the channel adapter (receives the Telegram webhook, calls the FastAPI
  API over HTTP, relays the response back to Telegram — channel-independent architecture per
  PRD RES-03); Neon (serverless Postgres) as the database.
- *Amendment 1 (2026-11-17, CHG-001):* n8n contains the orchestration of the demo (Telegram →
  pseudonymize → retrieval → Gemini → validation → Telegram, see
  `specs/003-n8n-migration/`); the Python code is kept in the repository (`kb/` ingestion into
  Neon still runs with `python -m app.infra.kb_ingest`).
- All secrets live in `.env` (never committed). *Amendment 1:* the demo's keys (Gemini, Telegram,
  Neon) live only in n8n credentials and never in exported workflow JSON.
- No data is sent to external model APIs that includes direct patient identifiers or raw health
  data; context is pseudonymized first (PRD RES-02).
- The system never writes to LifeCenter's clinical management software in v1.0; it operates on
  a project-owned schedule (PRD RES-01).

## Conventions
- Specs live under `specs/NNN-<feature>/`.
- Requirements use EARS notation.
- Knowledge artifacts follow the Open Knowledge Format (OKF).
- Agent behavior is governed by `AGENTS.md`.
- Each spec folder references the PRD requirement/story IDs it implements (e.g. `RF-001`,
  `US-001`, `SPEC-002`) to keep the traceability matrix in `docs/03-prd.md` §11 accurate.
