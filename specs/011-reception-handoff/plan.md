---
type: plan
spec_id: SPEC-010
title: reception handoff, complaints and ratings — Technical Plan
description: How to build the reception handoff, complaints and ratings — read-only preflight, recepcion.js and the consentimiento.js routing test-first, 007_reception.sql on the test branch then main, the group id stored by the human with a hidden prompt, A's changes through the MCP with pinned data, the Telegram test, and exports and docs. B and C's nodes do not change.
tags: [plan, reception, handoff, complaints, ratings, SPEC-010, n8n, neon]
status: implemented
sources: [./spec.md, ./clarifications.md, ../010-reminders/plan.md]
generated: { by: claude-code, at: 2026-11-24T00:00:00Z }
verified: { by: human, at: 2026-11-24T00:00:00Z }
stale_after: null
---

# reception handoff, complaints and ratings — Plan

Same pattern as SPEC-009: one step at a time, the human's confirmation before anything that
creates or changes objects in Neon or the workflows, and a warning before anything that
re-applies the schema, even on the test branch (human, 2026-11-24).

## Architecture

```text
A  … → Clasificar (~ consentimiento.js: group updates, handoff:<r>, hc:<code>, rt:<+|->, /queja)
     → ¿Qué ha llegado?
        ├─ group   → + Grupo de recepción: reply → Reenviar (decrypt, send to the patient)
        │                                  «Cerrar» → Cerrar handoff → edit the group message
        │                                  anything else → ignored (no reply)
        ├─ handoff → Decidir (consent) → + Recepción: confirm / «No» / awaiting_text
        ├─ rating  → Decidir (consent) → + Valoración (feedback_daily) → thanks, remove buttons
        └─ text    → … if a handoff is awaiting_text → Seudonimizar → Detectar urgencia
                       → + Publicar en el grupo → reply (urgency first, RH5)
     Componer respuesta (~ the handoff reason in the button; 👍/👎 under `answered`)

Neon: 007_reception.sql → reception_settings (group id, 1 row), reception_handoffs (code, reason,
      chat id encrypted with reminder_key, group message id, status, times), feedback_daily,
      handoff_* functions, handoff_purge (also called by reminder_claim_due), handoff_forget on
      withdrawal.
B: unchanged. C: its nodes unchanged; its claim function purges handoffs.
```

## Step 0: Preflight, read-only (AGENTS.md)

- Hosts of `DIRECT_URL` and `TEST_DATABASE_URL`, shortened; `Neon main` → `main` (credential
  metadata only).
- A, B and C published, draft = published = the export in git; their settings; no pinned data;
  no saved execution of A or C.
- Neon, both branches: SPEC-004 to SPEC-009 objects present; no `reception_*` or
  `feedback_daily` yet; the reminders and appointments counted, no subject or chat id printed.
- Nothing is created or changed.

## Step 1: The JavaScript, test-first (RH1–RH18)

- `n8n/code/recepcion.js` (new): the handoff codes, the reason per button, the texts,
  `GROUP_MESSAGE`, the strict complaint list (`evals/complaint_phrases.yaml`), and what to do with
  a group update.
- `consentimiento.js`: `classifyUpdate` returns `group` for any non-private chat; the new
  callbacks; `decide` for handoff, complaint and rating with and without consent. Urgency first.
- The keyboard of «Componer respuesta»: the reason in the handoff button and 👍/👎 only under
  `answered`.
- Red first, then green. The sync checks are skipped «hasta H4».

## Step 2: `007_reception.sql` on the test branch [confirmación] (RH19–RH22)

- `tests/infra/test_reception_sql.py` first (fake ids `901001…`, cleanup), then the SQL.
- Show the SQL, the commands and the host first. Running the full `tests/infra` re-applies the
  schema: say so before.

## Step 3: `main` [confirmación]

Read-only check before and after, as in SPEC-009 N3, plus `reception_settings` empty.

## Step 3b: The group id [humano] (D2)

A script in the scratchpad asks for the id with a hidden prompt and inserts it into
`reception_settings` on `main`. The agent then checks, read-only, that there is one row whose id
starts with `-100`, without printing it.

## Step 4: A through the MCP, with pinned data (RH1–RH18, RH23)

- List the nodes to add, change and rewire, and wait.
- Queries first on the test branch. Build from scripts that read the repo files; check with a CLI
  export.
- Pinned runs under the A4 extension (the spec's acceptance list), then `saveManualExecutions`
  off, no pinned data, B and C intact, and the executions for the human to delete.

## Step 5: Publish and test from Telegram [humano] (RH24)

- The human sets the group's auto-delete timer to 1 week, publishes A, and tests a handoff, a
  complaint, «Cerrar» and a rating.
- The agent checks read-only that the handoffs are deleted, the counts, and that A and C saved
  no executions.

## Step 6: Exports and docs

Export A from its published version; C and B unchanged. Scan (hosts, chat ids, the group id),
the Node tests, `pytest` (warning first). README (with the auto-delete setup step and the
limitation), `specs/index.md`, and spec, plan and tasks implemented.
