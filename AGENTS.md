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

## Git
- Do NOT commit unless the human explicitly asks.
- Never add Claude / any AI as co-author or collaborator. No `Co-Authored-By` lines.
  Commits are authored by the human.

## Layout
- `specs/`               SDD artifacts (OKF)
- `.env` / `.env.example`  environment variables
- `AGENTS.md`            this file — single source of truth for agent behavior
- `CLAUDE.md`            pointer to this file
