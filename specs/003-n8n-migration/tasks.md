---
type: tasks
spec_id: CHG-001
title: n8n-migration — Task Breakdown (demo MVP)
description: Ordered tasks to build and demo the single n8n workflow from Telegram.
tags: [tasks, change, n8n-migration, CHG-001, demo]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-17T00:00:00Z }
verified: { by: human, at: 2026-11-17T00:00:00Z }
stale_after: null
---

# n8n-migration — Tasks (demo MVP)

Steps marked **[humano]** need the human's accounts, browser or secrets. The Python code and its
tests stay untouched and must keep passing.

- [x] N0 — Setup **[humano + agente]** — done 2026-11-18 (n8n 2.48.4; MCP over OAuth on
  localhost via `N8N_EDITOR_BASE_URL`; the three credentials listed by name; Funnel answers 404 on
  `/`, `/rest`, `/mcp-oauth`, `/mcp-server` and reaches n8n on `/webhook/…`):
  - [agente] create `n8n-start.ps1` (reads `N8N_WEBHOOK_URL` from `.env`, sets `WEBHOOK_URL`,
    runs `n8n start`) and document `N8N_WEBHOOK_URL` in `.env.example`;
  - [humano] Funnel for `/webhook` and, during development, `/webhook-test`;
  - [humano] upgrade n8n and start it with `.\n8n-start.ps1`;
  - [humano] create the owner, enable the instance-level MCP;
  - [humano] create the bot and the three credentials;
  - [agente] connect the MCP;
  - [humano] authorize it.

  Check: the agent lists the instance through MCP and sees the three credentials by name; the
  Funnel URL answers on `/webhook/…` but not on `/` · covers: D9, D10
- [x] N1 — Knowledge base in Neon `main` **[agente, con aprobación]**: check whether `kb_fragments`
  exists and has rows on `main`; if not, run `python -m app.infra.kb_ingest` (defaults to
  `DIRECT_URL` = `main`) after the human approves · check: 3 documents, 9 fragments · covers: D3
  — done 2026-11-18: already loaded (HOR-001, TAR-001, TRA-001 × 3 fragments, vigente desde
  01/01/2026, `ejemplo: true`; `spanish_unaccent` present); no ingest run.
- [ ] N2 — Workflow skeleton: Telegram Trigger, Switch, Code "Seudonimizar", Telegram "Responder"
  echoing the pseudonymized text · check: pinned-data runs of the SPEC-001 T2 cases (phone, DNI,
  email, "me llamo…", "soy alérgica…" unchanged); then [humano] a Telegram message with a phone
  number comes back with `[TELEFONO]`; a sticker gets the D12 text · covers: D2, D12
  — 2026-11-18: workflow `q3f5dVrl8OUsXJrG` created; JS port passes the 36 T2 cases locally
  (Node) and the pinned run (execution 20) matches; pending the human Telegram check.
- [ ] N3 — Retrieval and threshold: Postgres "Buscar en kb", IF, Code "Abstención" · check:
  "¿Cuánto cuesta una limpieza?" → `top_score ≥ 0.01` with `TAR-001` first; "¿Aceptáis el seguro
  de Sanitas?" → abstention message · covers: D3, D4
- [ ] N4 — Generation: Code "Preparar prompt", HTTP Request "Gemini", Code "Error" · check: the
  request body carries the T6 system prompt verbatim and the schema; a forced bad model name
  produces the error message after one call · covers: D5, D7
- [ ] N5 — Validation: Code "Validar y componer" · check: pinned replies from SPEC-001 T5 — a
  correct cited 60 € passes with both notices; 65 €, "sesenta euros", `[TAR-001]` and an unknown
  ID end in abstention · covers: D6
- [ ] N6 — Handoff button and callback text · check: abstention shows the button; tapping it
  replies with the D8 text · covers: D8
- [ ] N7 — Demo run **[humano]**: unpublish `/webhook-test` from Funnel, activate the workflow and
  send the acceptance messages of the
  spec from Telegram; the agent reviews the executions with the human · covers: all acceptance
  criteria
- [ ] N8 — Export and docs: export to `n8n/workflows/lifecenter-telegram-demo.json`, secret check,
  README "Demo" section (how to start n8n with Funnel, ingest `kb/`, activate the workflow),
  update `specs/index.md` · covers: D9, D11
