---
type: spec
spec_id: SPEC-005
title: pseudonymized-log — Functional Spec
description: Requirements to split the n8n demo into a channel workflow that stores nothing and a core workflow that stores only pseudonymized executions, and to delete stored executions after 30 days (US-007, NFR-08, RES-02, R-06), in EARS notation. Supersedes CHG-001 D11.
tags: [spec, pseudonymized-log, SPEC-005, US-007, NFR-08, RES-02, R-06]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md, ../003-n8n-migration/spec.md, ../004-urgencies/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# pseudonymized-log — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-007), §5.2 (NFR-08), §6 (RES-02), §8 (R-06), §9
(DEP-04). Changes the CHG-001 workflow (`specs/003-n8n-migration/`), whose **D11 it supersedes**,
and keeps SPEC-003 (`specs/004-urgencies/`) unchanged in behaviour. Decisions in
[clarifications](./clarifications.md).

## Context

Hoy n8n guarda cada ejecución completa: el mensaje original del paciente, su nombre y usuario de
Telegram y el id del chat. Además, no hay un plazo de borrado fijado. Esta spec divide la demo en
dos flujos:

- el flujo de canal recibe y responde por Telegram y no guarda nada;
- el flujo principal hace todo el trabajo con el texto ya seudonimizado y sí guarda sus
  ejecuciones, para que la demo siga mostrando el recorrido de cada mensaje.

Todo lo guardado se borra a los 30 días.

**Definitions.**

- *Personal data* (NFR-08, extended in clarifications Q2):
  - in the message text: name, phone, DNI/NIE and email;
  - from Telegram: profile names (`first_name`, `last_name`), `username`, user id and chat id.
- *Channel workflow (A)*: the existing `lifecenter-telegram-demo`. It keeps its id and its Telegram
  webhook, so nothing changes in Tailscale Funnel.
- *Core workflow (B)*: a new workflow, `lifecenter-demo-core`, called by A as a sub-workflow.
- *Stored execution data*: what n8n persists for an execution and shows in its Executions list.

## Requirements (EARS)

### Split (Q1, Q3)

- P1. A SHALL contain the Telegram Trigger, "¿Qué ha llegado?", "Seudonimizar", "Pedir texto",
  "Confirmar botón", "Responder recepción", the call to B, "¿Ofrecer recepción?", "Responder" and
  "Responder con botón".
- P2. B SHALL contain "Detectar urgencia", "¿Es urgencia?", "Buscar en kb", "¿Hay contexto?",
  "Abstención", "Preparar prompt", "Gemini", "Error" and "Validar y componer". Their logic does
  not change; only their references to the chat id are removed.
- P3. WHEN a text message arrives, A SHALL pseudonymize it, call B with the pseudonymized text,
  wait for B's result and send the reply to the chat that sent the message.
- P4. A SHALL handle non-text messages (D12) and the "Hablar con recepción" button (D8) on its
  own, without calling B.

### What B receives and stores (Q2, RES-02)

- P5. A SHALL pass B **only** the pseudonymized text (`question`). It SHALL pass no chat id, user
  id, Telegram name, username or any other identifier.
- P6. B SHALL return the reply fields (`text`, `handoff`, `reason`, plus the existing diagnostic
  fields such as `urgency_level`, `matched`, `failure`, `citations`, `model_answer` and `usage`).
  It SHALL return no identifier. A SHALL attach the reply to its own chat id.
- P7. B's stored execution data SHALL contain no personal data, except what pseudonymization
  cannot detect (clarifications, Known limitations).

### What A stores (Q1, Q4, A3)

- P8. A SHALL save **no** execution data: not for successful runs, not for failed runs, not for
  manual runs, and no execution progress.
  - **Accepted limitation** (human, 2026-11-20, found in task L6): n8n still writes A's running
    execution to its local database. On finishing it soft-deletes it, and the next hard-delete
    pass removes it **within about 15 minutes**.
  - It is never visible in the editor or through the MCP.
  - It is a blocking condition for real patients (DEP-04). See clarifications, Known
    limitations.
- P9. WHEN a message has been handled, n8n's Executions list SHALL show **no** entry for A. It
  SHALL show one entry for B for each text message that reached B.

### Retention (Q5, NFR-08)

- P10. `n8n-start.ps1` SHALL start n8n with `EXECUTIONS_DATA_PRUNE=true` and
  `EXECUTIONS_DATA_MAX_AGE=720` (30 days) for the whole instance, and SHALL print both values on
  start. The other pruning settings keep n8n's defaults.
- P11. n8n SHALL delete every stored execution older than 30 days, within one pruning cycle
  (clarifications A2).
- P12. Deletion SHALL be verified once with a short test: n8n started with
  `EXECUTIONS_DATA_MAX_AGE=1`, old test executions observed being deleted, then 720 restored. The
  test SHALL NOT require editing `.env` or the script by hand. How is decided in the plan.

### History, exports and documentation

- P13. WHEN the new scheme is published and tested, the human SHALL delete every execution stored
  before the switch from the n8n editor, because they contain raw messages and Telegram personal
  data (Q7). The task SHALL remind the human.
- P14. A and B SHALL be exported to `n8n/workflows/` with no secret and no personal data,
  following the CHG-001 procedure (with the `shared` block removed). A's export SHALL show its
  "save no executions" settings.
- P15. The SPEC-003 test's sync check SHALL look for "Detectar urgencia" in B's export.
- P16. The README "Demo" section SHALL describe the two workflows, where the path of each message
  is seen (B), the 30-day deletion, and the limitations of this spec.
- P17. The CHG-001 docs SHALL record that D11 is superseded by SPEC-005.

## Acceptance criteria

- [ ] From Telegram, every behaviour is unchanged:
  - the CHG-001 messages: limpieza, sábados, Sanitas, the name and phone message, the injection
    and a sticker;
  - the SPEC-003 messages: an urgent one, a severe one and a non-urgent one;
  - the button, which still gives the D8 text.
- [ ] After those messages, the Executions list shows **no** new entry for A, and one entry for B
  per text message that reached B (not for the sticker or the button).
- [ ] A scan of those B executions finds none of the following: the test chat id, the Telegram
  profile name, the username, "Ana García" or "612 345 678". The name and phone message shows
  only `[NOMBRE]` and `[TELEFONO]`.
- [ ] On start, `n8n-start.ps1` prints `EXECUTIONS_DATA_PRUNE=true` and
  `EXECUTIONS_DATA_MAX_AGE=720`.
- [ ] The short test with `EXECUTIONS_DATA_MAX_AGE=1` deletes executions older than one hour, and
  720 is restored afterwards.
- [ ] Both workflows are exported with no secret or personal data, and A's export shows its "save
  no executions" settings.
- [ ] `node n8n/code/urgencias.test.js` is green, with the sync check against B's export.
- [ ] The human has deleted the pre-switch history, and no execution older than the switch
  remains.

## Out of scope

- A pseudonymized log of our own in Neon. It remains an option for RF-008 (clarifications Q6).
- Grouping messages by conversation in B, and any keyed identifier.
- Consent (CONF-005), Telegram's own retention, n8n's console and log files, and backups of n8n's
  database.
- Changes to pseudonymization itself (SPEC-001 R4), to the urgency rules (SPEC-003) or to the
  answer rules (SPEC-001).
