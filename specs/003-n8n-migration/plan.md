---
type: plan
spec_id: CHG-001
title: n8n-migration — Technical Plan (demo MVP)
description: Node-by-node design of the single n8n demo workflow, its credentials, public exposure, export procedure and the Python ingestion it relies on.
tags: [plan, change, n8n-migration, CHG-001, demo]
status: verified
sources: [./spec.md, ./clarifications.md]
generated: { by: claude-code, at: 2026-11-17T00:00:00Z }
verified: { by: human, at: 2026-11-17T00:00:00Z }
stale_after: null
---

# n8n-migration — Plan (demo MVP)

## Architecture

```text
[python -m app.infra.kb_ingest] ──(once, after editing kb/)──▶ Neon main: kb_fragments

Telegram ──HTTPS (Tailscale Funnel, /webhook/ only)──▶ n8n: lifecenter-telegram-demo
  Telegram Trigger (message, callback_query)
   └─ Switch: callback? ──yes──▶ Telegram: D8 handoff text
                        └─no──▶ Code: Seudonimizar
                                 ▶ Postgres: Buscar en kb (one row: top_score + fragments json)
                                 ▶ IF: top_score ≥ 0.01 ──no──▶ Code: Abstención ─┐
                                      └─yes─▶ Code: Preparar prompt               │
                                              ▶ HTTP Request: Gemini ──error──▶ Code: Error ─┤
                                              ▶ Code: Validar y componer ──────────────────┤
                                                                                           ▼
                                                                         Telegram: Responder
```

One workflow, as requested; the one node added to the requested path is **Code: Preparar
prompt**, because the HTTP body needs the prompt text built from the fragments (T6 logic).

## Nodes

1. **Telegram Trigger** — credential `Telegram LifeCenter Bot`; updates `message` and
   `callback_query`.
2. **Switch** — `callback_query` present → node 10; text message → node 3; anything else (photo,
   sticker) → Telegram "Pedir texto" with the D12 text.
3. **Code: Seudonimizar** — JavaScript port of `pseudonymize.py` (same regexes and name rules,
   "soy X" excluded). Output: `{ chatId, question }` with the pseudonymized `question` only.
4. **Postgres: Buscar en kb** — credential `Neon main`. One query returning a single row, so the IF
   evaluates once:

   ```sql
   WITH q AS (
     SELECT replace(plainto_tsquery('spanish_unaccent', $1)::text, ' & ', ' | ')::tsquery AS tsq
   ), today AS (SELECT (now() AT TIME ZONE 'Europe/Madrid')::date AS d),
   hits AS (
     SELECT f.chunk_text, f.titulo, f.source_id, f.tipo, f.vigente_desde, f.ejemplo,
            ts_rank(f.search_vector, q.tsq, 32) AS score
     FROM kb_fragments f, q, today
     WHERE f.search_vector @@ q.tsq
       AND f.vigente_desde = (SELECT max(v.vigente_desde) FROM kb_fragments v
                              WHERE v.source_id = f.source_id AND v.vigente_desde <= today.d)
     ORDER BY score DESC LIMIT 5
   )
   SELECT coalesce(max(score), 0) AS top_score,
          coalesce(json_agg(hits ORDER BY score DESC), '[]') AS fragments
   FROM hits;
   ```

   `$1` is bound to the pseudonymized question (Query Parameters option), never concatenated.
   The `replace(... ' & ', ' | ')` and current-version filter are SPEC-002's, copied from
   `app/infra/kb_repository.py`.
5. **IF: ¿Hay contexto?** — `top_score >= 0.01` (SPEC-002 Q10).
6. **Code: Preparar prompt** — port of `prompt.py`: the system prompt verbatim, `<fragmento
   cita="[ID | vigente desde dd/mm/aaaa]" titulo="…">` blocks, `<pregunta>` with `<`/`>`
   neutralized. Builds the Gemini request body: `systemInstruction`, `contents`,
   `generationConfig.responseMimeType = "application/json"`, `responseSchema` (`answerable`
   boolean, `answer` string).
7. **HTTP Request: Gemini** — `POST https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent`;
   credential `Gemini API` (Header Auth `x-goog-api-key`); model name written in the URL (not a
   secret). The demo uses **`gemini-flash-lite-latest`**, an alias chosen for stability on the
   free tier; in production a concrete version must be pinned on a paid plan (see clarifications
   "Demo model"). History: `gemini-3.8-flash` → `gemini-3.1-flash-lite` (2026-11-18) →
   `gemini-flash-lite-latest` (2026-11-19), after 503 "high demand" errors and timeouts. Timeout
   **20 000 ms** in the demo (a
   deviation from NFR-01, see clarifications "Demo deviation from NFR-01"); **Retry on fail
   off**; On Error → "continue (using error output)" to node 9.
8. **Code: Validar y componer** — port of `citations.py`, `figures.py` (amounts and percentages as
   integers in hundredths, since JavaScript has no `Decimal`), `validation.py` and the notices of
   `messages.py`: parse `candidates[0].content.parts[0].text`; non-JSON or missing fields → error
   message; `answerable: false` or a validation failure → abstention message; otherwise answer +
   notices. Output `{ chatId, text, handoff: bool, reason }` — `reason` is visible in the
   execution for the demo.
9. **Code: Error** — the SPEC-001 error message, `handoff: true`, `reason: llm_error`.
   **Code: Abstención** (from node 5) — abstention message, `handoff: true`,
   `reason: below_threshold`.
10. **Telegram: Responder** — `chatId`, `text`; inline keyboard `[[{"text": "Hablar con
    recepción", "callback_data": "handoff"}]]` when `handoff` is true. For callbacks: answer the
    callback query and send the D8 text.

Fixed texts (abstention, error, notices, D8) are copied verbatim from
`app/domain/answering/messages.py` and the spec.

## Credentials (created by the human in the n8n UI)

| Name | Type | Value from |
|---|---|---|
| `Telegram LifeCenter Bot` | Telegram API | BotFather token |
| `Gemini API` | Header Auth (`x-goog-api-key`) | `GOOGLE_API_KEY` |
| `Neon main` | Postgres (SSL required) | host, database, user and password of `DATABASE_URL` |

The agent never reads or prints these values; workflows reference the credentials by name, and
the exported JSON only carries the credential name and id.

## Public exposure

- n8n is started with `n8n-start.ps1` (repo root), which reads `N8N_WEBHOOK_URL` from `.env`
  (e.g. `https://<machine>.<tailnet>.ts.net/`), sets `WEBHOOK_URL` for that process only and runs
  `n8n start`, so the Telegram Trigger registers the public URL with Telegram. The script loads no
  other variable from `.env`. It also fixes `N8N_EDITOR_BASE_URL=http://localhost:5678/`, because
  n8n derives the MCP OAuth issuer and endpoints from it (otherwise from `WEBHOOK_URL`, the public
  host, where `/mcp-oauth` is not published and client registration fails with 404).
- Tailscale Funnel maps only these paths:
  - always: `tailscale funnel --bg --set-path /webhook http://127.0.0.1:5678/webhook`;
  - **during development only**: `tailscale funnel --bg --set-path /webhook-test
    http://127.0.0.1:5678/webhook-test`, so the editor's "listen for test event" on the Telegram
    Trigger receives messages; removed before the demo with
    `tailscale funnel --set-path /webhook-test off`.

  The editor (`/`), `/rest`, `/api` and `/mcp-server` are never published.
- Telegram allows one webhook per bot: listening for a test event points the bot at
  `/webhook-test/…`, and activating (or re-activating) the workflow points it back at
  `/webhook/…`. The demo runs with the workflow **active**; its executions appear in the
  Executions list.

## Versioning

After each change: `n8n export:workflow --id=<id> --output=n8n/workflows/lifecenter-telegram-demo.json --pretty`,
then a check that the file contains no key/token (`grep` for `key`, `token`, `password`,
`postgres://`, `AIza`).

## Verification (no evals in this MVP)

- Node-level checks while building, with pinned data through the MCP `test_workflow` tool (no
  Telegram, no Gemini quota for the pure Code nodes): the pseudonymization cases of SPEC-001 T2
  and the validation cases of T5 (a handful each), compared by eye against the Python tests,
  which remain in the repo and keep passing.
- End-to-end: the acceptance messages of the spec, sent from Telegram by the human.

## Requirement → Component map

| Requirement | Component |
|---|---|
| D1 | the whole workflow |
| D2 | node 3 |
| D3 | node 4 |
| D4 | nodes 5, 9 (abstención) |
| D5 | nodes 6, 7 |
| D6 | node 8 |
| D7 | nodes 7 (error output), 9 |
| D8 | nodes 2, 10 |
| D9 | credentials table; export check |
| D10 | Funnel paths (`/webhook`, `/webhook-test` in development); `n8n-start.ps1` |
| D11 | workflow setting "save executions" left on; clarifications |
| D12 | nodes 2 (fallback output), "Pedir texto" |
