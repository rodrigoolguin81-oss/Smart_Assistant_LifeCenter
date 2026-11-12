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
| `status` | `draft` \| `active` \| `verified` \| `implemented` \| `deprecated`. For a feature's spec/plan/tasks the lifecycle is `draft` → `verified` (a human confirmed the content) → `implemented` (all its tasks are done and their tests pass) → `deprecated`. |
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
4. Install, test and run the retrieval tooling (SPEC-002). Requires Python ≥ 3.12 and these
   variables in `.env` (see `.env.example`): `DATABASE_URL` (pooled, used by the API),
   `DIRECT_URL` (direct, used by ingestion for DDL), `TEST_DATABASE_URL` (direct connection to the
   dedicated Neon `test` branch) and, optionally, `RETRIEVAL_RELEVANCE_THRESHOLD`.

   ```bash
   # Install the package and dev dependencies into the project virtualenv
   python -m venv .venv
   source .venv/Scripts/activate     # Windows Git Bash (PowerShell: .venv\Scripts\Activate.ps1;
                                     # macOS/Linux: source .venv/bin/activate)
   pip install -e ".[dev]"

   # Run the test suite — database tests only ever use TEST_DATABASE_URL, never main
   pytest

   # Ingest kb/ into the database: applies the schema, then fully replaces kb_fragments.
   # Uses DIRECT_URL (the main branch) by default — run it deliberately, after editing kb/.
   python -m app.infra.kb_ingest

   # Retrieval eval (NFR-05, Recall@5): re-ingests kb/ into the test branch and reports the
   # result; exits non-zero below 90%. Uses TEST_DATABASE_URL and refuses to run against main.
   python -m evals.eval_retrieval
   ```

## Git rule

No automatic commits, and no AI co-authorship or collaborator access: every commit is authored
by a human, with no `Co-Authored-By` lines for any AI agent.

## Agent rules

Any AI agent working in this repo must follow **[AGENTS.md](./AGENTS.md)** — it is the single
source of truth for agent behavior, and `CLAUDE.md` only points to it.
