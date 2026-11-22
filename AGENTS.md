# Agent operating instructions

These rules apply to ANY AI agent working in this repository (Claude Code, and others).
Project principles live in `specs/constitution.md` (OKF) — read that first; this file is the
operational layer on top of it.

## Golden rules
- Spec-first: never write application code before its spec/plan/tasks exist under
  `specs/NNN-<feature>/`.
- Clarify before specifying: ask open questions and WAIT for human answers before writing a spec.
- TDD: a failing test precedes every implementation task.
- Secrets: live only in `.env` (never committed). Document keys in `.env.example`.
- Knowledge artifacts use the Open Knowledge Format (OKF): markdown + YAML frontmatter.

## Workflow
Constitution → Clarify → Spec (EARS) → Plan → Tasks → Implement (TDD) → Validate → Change

## Preflight check (first task of every spec that touches n8n or Neon)
- Before building anything, verify which database each n8n credential really reaches. Check
  the **host**, not only the user and the database name: Neon `main` and the test branch share
  user (`neondb_owner`) and database (`neondb`), so only the host tells them apart.
- n8n credentials cannot be read. Compare with `.env` (`DIRECT_URL` vs `TEST_DATABASE_URL`, host
  only, never the password or the full URL). Confirm with a write the feature makes on purpose
  (or a known row), read back from `main`.
- `Neon main` must point to `main`, with the certificate fields (CA Certificate, Client Private
  Key, Client Certificate) empty. Browsers autofill them.
- Why: in SPEC-006 (task K5, 2026-11-22) `Neon main` pointed to the test branch. The bot was
  reading and writing data that `pytest tests/infra` rewrites.

## Git
- Do NOT commit unless the human explicitly asks.
- Never add Claude / any AI as co-author or collaborator. No `Co-Authored-By` lines.
  Commits are authored by the human.

## Layout
- `specs/`               SDD artifacts (OKF)
- `.env` / `.env.example`  environment variables
- `AGENTS.md`            this file — single source of truth for agent behavior
- `CLAUDE.md`            pointer to this file
