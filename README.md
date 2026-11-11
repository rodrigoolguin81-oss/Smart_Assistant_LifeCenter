# Smart Assistant - LifeCenter

A Telegram assistant for LifeCenter, a dental clinic, that answers frequent patient questions
(prices, schedules, insurance, aftercare) via RAG over the clinic's knowledge base, and manages
appointments on a project-owned schedule — offloading repetitive queries from reception while
escalating anything clinical, urgent, or a complaint to a human. See `docs/01-charter.md` and
`docs/03-prd.md` for the full charter and PRD.

## How we work (Spec-Driven Development)

This repo follows SDD:

```
Constitution → Clarify → Spec (EARS) → Plan → Tasks → Implement (TDD) → Validate → Change
```

- **Constitution** (`specs/constitution.md`) — project-wide principles and constraints.
- **Clarify** — before any spec is written, open questions about the feature are asked and
  answered by a human (or explicit assumptions are recorded). See `specs/NNN-<feature>/clarifications.md`.
- **Spec** — functional requirements in EARS notation (`spec.md`).
- **Plan** — architecture, module boundaries and contracts (`plan.md`).
- **Tasks** — granular, test-first tasks mapped to requirements (`tasks.md`).
- **Implement** — TDD: a failing test precedes every implementation task.
- **Validate / Change** — acceptance criteria are checked; any change to a shipped spec goes
  through the same gate again.

No application code is written before its spec, plan and tasks exist under `specs/NNN-<feature>/`.

## Add a new feature

1. Create `specs/NNN-<feature-slug>/` (next incremental number).
2. Go through the Clarify gate: ask 3-7 pointed questions about scope, actors, data, edge cases,
   constraints and acceptance criteria, and wait for answers before writing anything else.
   Record questions, answers and any explicit assumptions in `clarifications.md`.
3. Write `spec.md` (EARS requirements), then `plan.md` (architecture/contracts), then `tasks.md`
   (test-first tasks), each referencing the previous as its `sources`.
4. Add an entry to `specs/index.md`.

## Open Knowledge Format (OKF)

Every knowledge artifact in `specs/` is plain Markdown with YAML frontmatter:

| Field | Meaning |
|---|---|
| `type` | Document kind: `constitution`, `clarifications`, `spec`, `plan`, `tasks`, `index`. |
| `title` / `description` | Human-readable summary. |
| `tags` | Categorical labels. |
| `status` | `draft` \| `active` \| `verified` \| `deprecated`. |
| `sources` | Documents this one derives from (relative paths or URLs). |
| `generated` | `{ by, at }` — creation metadata. |
| `verified` | `{ by, at }` — `null` until a human confirms it. |
| `stale_after` | Expiry date/condition, or `null`. |

Documents link to each other with relative Markdown links (e.g. `[plan](./plan.md)`).

## Setup

1. Copy `.env.example` to `.env` and fill in the real values (never commit `.env`).
2. Initialize Neon: `npx neon@latest init`, then paste the pooled connection string into
   `DATABASE_URL` and the direct/unpooled one into `DIRECT_URL`.
3. (Pending) Stand up the n8n instance (Docker + Tailscale Funnel) and register the n8n MCP
   server and skills once it's reachable — see `AGENTS.md` and `.env.example` for the
   `N8N_BASE_URL` / `N8N_MCP_TOKEN` placeholders.
4. Run the test suite once application code exists (none yet — scaffolding only).

## Git rule

No automatic commits, and no AI co-authorship or collaborator access: every commit is authored
by a human, with no `Co-Authored-By` lines for any AI agent.

## Agent rules

Any AI agent working in this repo must follow **[AGENTS.md](./AGENTS.md)** — it is the single
source of truth for agent behavior, and `CLAUDE.md` only points to it.
