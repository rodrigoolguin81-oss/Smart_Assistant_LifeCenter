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
- [x] N2 — Workflow skeleton: Telegram Trigger, Switch, Code "Seudonimizar", Telegram "Responder"
  echoing the pseudonymized text · check: pinned-data runs of the SPEC-001 T2 cases (phone, DNI,
  email, "me llamo…", "soy alérgica…" unchanged); then [humano] a Telegram message with a phone
  number comes back with `[TELEFONO]`; a sticker gets the D12 text · covers: D2, D12
  — 2026-11-18: workflow `q3f5dVrl8OUsXJrG` created; JS port passes the 36 T2 cases locally
  (Node) and the pinned run (execution 20) matches. Telegram check by the human, executions
  21–33 reviewed: phone → `[TELEFONO]`, email → `[EMAIL]`, "me llamo …" → `[NOMBRE]`; "soy
  diabetico", prices, times and "para mi hermana" unchanged; an image → D12 text. Execution 25
  ("la cita va con <nombre completo>") kept the name: the known Q5 limitation (no introduction).
- [x] N3 — Retrieval and threshold: Postgres "Buscar en kb", IF, Code "Abstención" · check:
  "¿Cuánto cuesta una limpieza?" → `top_score ≥ 0.01` with `TAR-001` first; "¿Aceptáis el seguro
  de Sanitas?" → abstention message · covers: D3, D4
  — 2026-11-18: SQL run read-only on `main` (limpieza 0.0436 with TAR-001 first; Sanitas 0 rows;
  sábados 0.0247 with HOR-001 first); nodes added with a temporary "Contexto encontrado (N3)"
  reply (removed in N4) and the "Hablar con recepción" button; pinned run (execution 34) routes
  both cases correctly. Human Telegram check reported done; the saved executions after
  publishing show only execution 35 (real Neon query, no context → abstention with button).
- [x] N4 — Generation: Code "Preparar prompt", HTTP Request "Gemini", Code "Error" · check: the
  request body carries the T6 system prompt verbatim and the schema; a forced bad model name
  produces the error message after one call · covers: D5, D7
  — 2026-11-18: "Contexto encontrado (N3)" replaced by Preparar prompt → Gemini (Header Auth
  `Gemini API`, `gemini-3.8-flash`, 4 000 ms, no retries, error output) → Error; temporary
  "Respuesta sin validar (N4)" until N5. Pinned run (execution 36): system prompt 1 520 chars,
  verbatim; schema answerable/answer; `<` `>` neutralized; `[NOMBRE]` in the body; non-JSON reply
  → error message with button. First real call (execution 37): `timeout` after 4 s
  (ECONNABORTED, no HTTP code) — the D7 path works. Direct probes: `gemini-3.8-flash` timeouts and
  503 "high demand"; switched to `gemini-3.1-flash-lite` (4/4 HTTP 200, 1.6–2.5 s). Pending:
  publish, real Gemini answer from Telegram, forced bad model name. Execution 38 (published
  `gemini-3.1-flash-lite`) also hit `timeout` at 4 s → timeout raised to 10 000 ms, then 20 000 ms, for the demo
  (clarifications "Demo deviation from NFR-01"). 3 direct calls with the real 5-fragment prompt:
  1.26 s, 1.03 s, 17.22 s (all HTTP 200, 60 € with the TAR-001 citation). Published version with
  20 000 ms: executions 39 (limpieza → 60 € with TAR-001, ~3.7 s) and 40 (sábados → 10:00–14:00
  with HOR-001, ~2.3 s). No Sanitas execution was saved after publishing. The forced bad model
  name was not run: the D7 path was instead exercised by the real timeouts (executions 37, 38).
- [ ] N5 — Validation: Code "Validar y componer" · check: pinned replies from SPEC-001 T5 — a
  correct cited 60 € passes with both notices; 65 €, "sesenta euros", `[TAR-001]` and an unknown
  ID end in abstention · covers: D6
  — 2026-11-18: "Respuesta sin validar (N4)" replaced by "Validar y componer" (JS port of
  citations/figures/validation with integer hundredths, plus the R12/R13 notices). The port
  passes 80 local cases (Node): every case of the Python T3–T5 tests plus compose cases. Pinned run
  (execution 41): 60 € → answer + price + example notices; 65 € → `figure_not_in_source`;
  "sesenta euros" → `unvalidatable_currency`; `[TAR-001]` → `malformed_citation`; TAR-999 →
  `unknown_citation`; `answerable: false` → `model_abstained`; a time answer → example notice only.
  Pending: publish and Telegram check. Published 2026-11-19: execution 42 → Gemini HTTP 503
  "high demand" in 1.8 s (`api_error`); execution 43 → timeout at 20 s (`timeout`). Benchmark the
  same day (3 calls/model, real body, 25 s cap; then a sequential rerun of the candidates):
  `gemini-flash-lite-latest` 6/6 HTTP 200 (3.9–17.7 s); `gemini-3.1-flash-lite` 5/6 (one
  timeout; 5.2–20.9 s); `gemini-3-flash-preview` 4/6 (2.7–5.0 s in the rerun, but one timeout and
  one 503 before); the 3.5–3.8 Flash models and `gemini-flash-latest` mostly 503/429/timeout;
  `gemini-2.5-flash-lite` 404. Human chose `gemini-flash-lite-latest` (alias; see clarifications
  "Demo model"); timeout kept at 20 s.
- [ ] N6 — Handoff button and callback text · check: abstention shows the button; tapping it
  replies with the D8 text · covers: D8
- [ ] N7 — Demo run **[humano]**: unpublish `/webhook-test` from Funnel, activate the workflow and
  send the acceptance messages of the
  spec from Telegram; the agent reviews the executions with the human · covers: all acceptance
  criteria
- [ ] N8 — Export and docs: export to `n8n/workflows/lifecenter-telegram-demo.json`, secret check,
  README "Demo" section (how to start n8n with Funnel, ingest `kb/`, activate the workflow),
  update `specs/index.md` · covers: D9, D11
