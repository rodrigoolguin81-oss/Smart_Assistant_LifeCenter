---
type: clarifications
spec_id: CHG-001
title: n8n-migration — Clarifications
description: Decisions taken with the human to move the whole application (SPEC-002 retrieval and ingestion, SPEC-001 answer generation) from Python/FastAPI to n8n, plus assumptions, losses accepted and known limitations.
tags: [clarify, change, n8n-migration, CHG-001, SPEC-001, SPEC-002]
status: verified
sources: [../constitution.md, ../001-rag-retrieval/spec.md, ../002-answer-generation/spec.md]
generated: { by: claude-code, at: 2026-11-17T00:00:00Z }
verified: { by: human, at: 2026-11-17T00:00:00Z }
stale_after: null
---

# n8n-migration — Clarifications

## Scope reduction to a demo MVP (human, 2026-11-17) — supersedes the decisions below

New context: there is no defense; the deliverable is a **demo** showing Telegram messages and
their path through n8n workflows. CHG-001 is reduced to:

- **One main workflow:** Telegram Trigger → Code (pseudonymize, SPEC-001 logic) → Postgres (the
  SPEC-002 FTS over `kb_fragments` in Neon) → IF threshold → Gemini via HTTP with structured
  output (T6 prompt) → Code (validate citation and figures, T5 logic) → Telegram. Abstention uses
  the fixed SPEC-001 message.
- **Executions ARE saved** (that is the demo). This stores the raw Telegram message: accepted for
  the demo with team messages only; **in production this must be revisited for privacy**
  (RES-02, former D1).
- **Keys (Gemini, Telegram, Neon) only in n8n credentials**, never in the JSON; the workflow is
  exported to `n8n/workflows/`.
- **Funnel only for `/webhook/`** (former D4).
- **Handoff button text (former D6):** "Ahora mismo no puedo pasar tu consulta automáticamente.
  Llama a recepción en horario de atención."
- **The Python code stays in the repo; nothing is deleted.** `kb/` ingestion into Neon keeps
  running with `python -m app.infra.kb_ingest`.
- **No evaluations and no extra workflows for now.**

Consequences for the record below: Q1 (delete Python), Q2/Q5/Q7 (evaluations, datasets), Q6 (credentials
created from `.env` via the API — now created by the human in the n8n UI), D1, D2, D3, D5 are
**superseded**; Q3 (JavaScript), Q4/Q8 (MCP from Claude Code; export to `n8n/workflows/`) and D4
**stand**. SPEC-001 T8–T16 stay pending and are not part of the demo.

## Original record (before the scope reduction)

**Change CHG-001** (workflow phase "Change"). On 2026-11-17 the human decided to build the whole
project in n8n instead of Python/FastAPI with n8n as a mere channel adapter. At that point SPEC-002
was implemented in Python, and SPEC-001 had T0–T7 implemented (pure domain logic, 256 tests,
commit `946162b`); T8–T16 were pending.

The **behavior** specified in SPEC-002 (R1–R11) and SPEC-001 (R4–R19) is kept, except where this
change says otherwise. What changes is **where it runs** (n8n), **how it is verified** (evals
instead of TDD) and **how the channel reaches it** (Telegram through n8n from the start).

## Questions & answers

- Q1: What happens to the existing Python code (`app/`, `tests/`, `evals/*.py`)?
  → A: **Everything moves to n8n, including `kb/` ingestion; the Python code is deleted** in a
  commit of its own. It remains in git history (`946162b`) as the reference for the logic and its
  edge cases while they are ported. FastAPI disappears.

- Q2: The constitution required TDD. How is the logic inside n8n verified?
  → A: **n8n Evaluations.** The constitution is amended (Amendment 1) from "Test-Driven" to
  "Eval-driven". The edge cases of the deleted Python tests are carried over as evaluation cases
  (see Q5).

- Q3: Language of the Code nodes?
  → A: **JavaScript** (native to n8n, no extra configuration). Consequence: there is no `Decimal`;
  euro amounts and percentages are compared as **integers in hundredths** (cents) after the same
  separator rule, never as floats.

- Q4: How are workflows built and versioned?
  → A: **Through n8n itself, driven by the agent**: the instance-level **MCP server** of n8n
  (connected to Claude Code; tools such as `create_workflow_from_code`, `update_workflow`,
  `validate_workflow`) for building and editing, and the **n8n REST API** (`N8N_API_KEY` in
  `.env`) for what MCP cannot do — notably creating credentials. After every change the workflow
  is **exported as JSON to `n8n/workflows/`** so git holds it.

- Q5: n8n Community Edition allows metric-based evaluations in **a single workflow** only, and
  requires a registered instance. How is evaluation organized?
  → A: **Register the instance (free) and use one metric-based evaluation workflow** covering
  NFR-03, figure attribution, false abstention and NFR-06 as custom 0/1 metrics, with a separate
  Gemini node as judge (a model different from the generator). Deterministic rules
  (pseudonymization, citations, figures, validation) are checked with **light evaluations**,
  which have no workflow limit on a registered Community instance.

- Q6: The constitution keeps secrets only in `.env`, but n8n stores credentials in its own
  encrypted store. How is that reconciled?
  → A: **`.env` stays the single source.** n8n credentials (Gemini, Telegram, Neon) are created
  from `.env` through the n8n REST API; workflows reference them by name only; no secret value
  appears in workflow JSON, git or agent output. Constitution Amendment 1 records this.

- Q7: Where do the evaluation datasets live?
  → A: **YAML files in `evals/`** (versioned source of truth) are **loaded into n8n Data Tables**
  through the API before each evaluation run. No Google Sheets.

- Q8: Can the work continue from Claude Code?
  → A: Yes, through the n8n instance-level MCP server, connected with
  `claude mcp add --transport http n8n http://localhost:5678/mcp-server/http` and OAuth (`/mcp`),
  so no token is stored in a file. n8n is upgraded to ≥ 2.33.0 (the documented "Connect a client"
  flow requires it; 2.32.6 is installed). Workflows built by the agent must be marked
  "Available in MCP" so it can read and edit them in full.

## Decisions taken by the agent while writing the plan (to be confirmed at review)

- **D1 — Raw message never stored by n8n.** n8n saves execution data, and the channel workflow
  receives the raw Telegram message (with possible identifiers). To keep SPEC-001 R5 / RES-02, the
  **channel workflow pseudonymizes first and is configured to save no execution data** (success
  and error); only the core workflow, which receives the pseudonymized text, keeps executions.
- **D2 — Non-secret configuration in a Data Table `settings`.** Community Edition has no custom
  variables, and n8n 2.x blocks environment access from Code nodes by default. Model names,
  timeout, prices and the relevance threshold are loaded from `.env` into a `settings` Data Table
  by the same bootstrap step that creates credentials.
- **D3 — A protected test webhook replaces the FastAPI endpoint.** SPEC-001 R1–R3 (endpoint,
  shared-secret header, loopback) are re-stated for an n8n webhook `POST /webhook/answer`
  protected with Header Auth (`X-Api-Token` = `CONVERSATION_API_TOKEN`), used for manual tests and
  the load test. Telegram uses its own trigger.
- **D4 — Public exposure limited to webhooks.** Tailscale Funnel publishes only the `/webhook/`
  path of n8n (needed by Telegram); the editor, the REST API and the MCP endpoint stay local.
- **D5 — 429 handling only in the evaluation workflow.** The core workflow still makes one model
  call with no retries (SPEC-001 Q12); n8n's "Retry on fail" is **off** on the model node. The
  evaluation workflow waits and re-runs a case when the core returns
  `error_kind = rate_limited`, and counts the 429s.
- **D6 — "Hablar con recepción" button.** The channel workflow shows the button when
  `offer_handoff` is true; handling the tap (recording the handoff, notifying reception) belongs to
  RF-007 and stays out of scope. Until then the tap gets a fixed acknowledgement — wording to be
  confirmed by the human (proposed: "De acuerdo. Recepción revisará tu consulta en horario de
  atención.").

## Losses accepted with this change

- The fast deterministic test suite (256 pytest tests run in ~30 s) is replaced by evaluation
  cases run inside n8n — slower and less granular.
- Exact `Decimal` arithmetic becomes integer-cents arithmetic in JavaScript (equivalent for the
  formats in scope, but a re-implementation that must be re-verified).
- Metric-based evaluations run sequentially on Community Edition (parallelism 1), so the
  50-question eval is slower.
- Workflow JSON diffs are harder to review than Python diffs.

## Assumptions

- The n8n instance is the project-local one (npm global install), upgraded to ≥ 2.33.0 and
  registered as Community.
- Everything decided in SPEC-001 and SPEC-002 clarifications (threshold 0.01, Gemini free tier for
  development only, no real patients until SPEC-003, provisional notices pending CONF-002, figure
  normalization rules, attribution limitation) still applies.
- Durations, attribution traps and injection cases already planned for the SPEC-001 evals are
  carried into the n8n evaluation datasets unchanged.
