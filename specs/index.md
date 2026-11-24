---
type: index
title: Smart Assistant - LifeCenter — Specs Index
description: Index of all SDD artifacts (constitution and per-feature spec/plan/tasks folders).
tags: [index, sdd]
status: draft
sources: []
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: null }
stale_after: null
---

# Specs Index

- [constitution](./constitution.md) — project-wide principles, constraints and conventions.
- **001-rag-retrieval** — knowledge base indexing and lexical retrieval (PRD `RF-001`, `RF-002`,
  traceability row **SPEC-002**) — **implemented** (2026-11-12; tasks T0–T11 done, R1–R11):
  - [clarifications](./001-rag-retrieval/clarifications.md) — includes the relevance threshold
    decision (Q10) and known limitations (vocabulary mismatch)
  - [spec](./001-rag-retrieval/spec.md)
  - [plan](./001-rag-retrieval/plan.md)
  - [tasks](./001-rag-retrieval/tasks.md)
  - Code: `app/` · tests: `tests/` · evals: `evals/` (`eval_retrieval` Recall@5 = 91.3% on the
    interim dataset; `abstention_dataset.yaml` kept for SPEC-001's NFR-03 eval)
  - Open follow-ups: recalibrate retrieval (eval + threshold) with real data once PRD DEP-01 is
    delivered; revisit the threshold if SPEC-001 misses NFR-03 end to end.

- **002-answer-generation** — grounded answer generation with layered deterministic abstention,
  citation + figure validation and pseudonymization (PRD `RF-002`, `RF-003`, `US-001`, `US-002`,
  `NFR-03`, `NFR-06`, `RES-02`, traceability row **SPEC-001**) — **specified** (2026-11-13; spec
  verified by human; plan and tasks verified 2026-11-16; Python T0–T7 done at `946162b`; T8–T16
  paused while the n8n demo (CHG-001) is built, which ports T2, T5 and T6 logic):
  - [clarifications](./002-answer-generation/clarifications.md) — Q1–Q15, including the Gemini
    free-tier condition (dev only) and the SPEC-003 precondition for real patients
  - [spec](./002-answer-generation/spec.md)
  - [plan](./002-answer-generation/plan.md) — includes the figure normalization rule
  - [tasks](./002-answer-generation/tasks.md) — T0–T16

- **003-n8n-migration** — change **CHG-001**, reduced to a **demo MVP**: one n8n workflow
  (Telegram → pseudonymize → Neon FTS → threshold → Gemini → validation → Telegram); Python code
  and `kb/` ingestion kept; constitution Amendment 1 — **implemented** (2026-11-19; N0–N8 done, all
  acceptance criteria met from Telegram). Demo
  deviations: Gemini timeout 20 s (NFR-01 not met) and model alias `gemini-flash-lite-latest` on
  the free tier:
  - [clarifications](./003-n8n-migration/clarifications.md) — scope reduction on top
  - [spec](./003-n8n-migration/spec.md) — D1–D12
  - [plan](./003-n8n-migration/plan.md) — node-by-node design
  - [tasks](./003-n8n-migration/tasks.md) — N0–N8
  - Workflow: [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)
    · how to run it: README, "Demo (n8n + Telegram)"

- **004-urgencies** — deterministic symptom/urgency detection in the n8n demo workflow, fixed
  two-level reply with the clinic's urgency phone, never reaching Gemini (PRD `US-003`, `RF-004`,
  `NFR-04`, `RES-04`, `CONF-003`, `R-02`, traceability row **SPEC-003**) — **implemented for
  the demo** (2026-11-19; U0–U5 done; NFR-04 30/30 on the dataset with 0 false positives; every
  acceptance criterion met from Telegram. The clinical review by Prince Calderon is **pending**:
  the criteria stay provisional and opening to real patients stays blocked. Example phone
  `000 000 000` until DEP-01):
  - [clarifications](./004-urgencies/clarifications.md)
  - [spec](./004-urgencies/spec.md) — U1–U19
  - [plan](./004-urgencies/plan.md) — normalization, rules, test and workflow wiring
  - [tasks](./004-urgencies/tasks.md) — U0–U5
  - Code: [`n8n/code/urgencias.js`](../n8n/code/urgencias.js) · test
    `node n8n/code/urgencias.test.js` · dataset
    [`evals/urgency_dataset.yaml`](../evals/urgency_dataset.yaml)

- **005-pseudonymized-log** — split the n8n demo into a channel workflow that stores nothing and
  a core workflow with pseudonymized executions only, deleted after 30 days (PRD `US-007`,
  `NFR-08`, `RES-02`, `R-06`; new traceability row **SPEC-005**; supersedes CHG-001 D11) —
  **implemented for the demo** (2026-11-20; L0–L7 done; 7 of 8 acceptance criteria met. L6 was
  closed by checking the configuration only: the short test never ran because port 5678 was
  already in use, so the **real deletion test is pending**. `n8n-start.ps1` now refuses to start
  when the port is in use. Accepted limitation: A's running execution stays in n8n's local
  database for up to about 15 minutes, which blocks real patients until DEP-04):
  - [clarifications](./005-pseudonymized-log/clarifications.md)
  - [spec](./005-pseudonymized-log/spec.md) — P1–P17
  - [plan](./005-pseudonymized-log/plan.md) — Steps 0–7
  - [tasks](./005-pseudonymized-log/tasks.md) — L0–L7
  - Workflows: [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)
    (A, channel, saves nothing) and
    [`n8n/workflows/lifecenter-demo-core.json`](../n8n/workflows/lifecenter-demo-core.json) (B,
    core, executions kept 30 days) · retention: `n8n-start.ps1 -ExecutionsMaxAgeHours`

- **006-consent** — explicit consent in the bot's first message in the n8n demo: notice with
  «Acepto» / «No acepto», `/privacidad` and withdrawal, urgencies always answered (detected in A),
  no call to B before consent, and a minimal consent record in Neon keyed by an HMAC of the
  Telegram `from.id` (PRD `CONF-005`, `R-06`, `DEP-04`, `RES-02`, `RF-004`; new traceability row
  **SPEC-006**; RF-006 reminders will reuse it) — **implemented for the demo** (2026-11-22; K0–K6
  done; every acceptance criterion met, by Node and SQL tests, 17 pinned runs and the Telegram
  test). Found and fixed in K5: the `Neon main` credential pointed to the test branch; it now
  points to `main`, and AGENTS.md requires checking each credential's host. Accepted
  limitations: the HMAC key is in the same database as the records, and must never be
  regenerated. Still provisional until DEP-04, so real patients stay blocked:
  - [clarifications](./006-consent/clarifications.md)
  - [spec](./006-consent/spec.md) — C1–C27
  - [plan](./006-consent/plan.md) — Steps 0–6
  - [tasks](./006-consent/tasks.md) — K0–K6
  - Code: [`n8n/code/consentimiento.js`](../n8n/code/consentimiento.js) · test
    `node n8n/code/consentimiento.test.js` · SQL
    [`app/infra/sql/002_consent.sql`](../app/infra/sql/002_consent.sql), tested by
    `tests/infra/test_consent_sql.py` (test branch only)
  - Workflow: A, [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json)

- **007-agenda** — the project's own appointment agenda in Neon (RES-01). It holds opening hours,
  professionals with roles (dentist / hygienist), rooms and appointment types. It has a free-slot
  lookup and a booking primitive that never double-books (NFR-07, R-05), at most 1 future
  appointment per patient, and a pseudonymous subject (SPEC-006 key, `agenda:` prefix) kept 30
  days. There is no patient-facing flow and no n8n change. PRD `RF-005` (agenda base), `NFR-07`,
  `R-05`, `CONF-001` (option a), `DEP-03`; traceability row **SPEC-004**. Status:
  **implemented** (2026-11-22; E0–E4 done; all 14 acceptance criteria met, with 58 SQL tests on
  the test branch including NFR-07, then applied to `main` with `kb_fragments`, `consent` and the
  key unchanged). Patients book on it through SPEC-007 (008-booking). Moving and cancelling, and
  reminders, are later specs. Example data until DEP-01 and DEP-03:
  - [clarifications](./007-agenda/clarifications.md) — Q1–Q14
  - [spec](./007-agenda/spec.md) — G1–G23
  - [plan](./007-agenda/plan.md) — Steps 0–4 (public functions use `now()`; internal `_at`
    versions for the tests)
  - [tasks](./007-agenda/tasks.md) — E0–E4
  - Code: [`app/infra/sql/003_agenda.sql`](../app/infra/sql/003_agenda.sql) · tests
    `tests/infra/test_agenda_sql.py` (test branch only) · README, "Agenda (SPEC-004)"

- **008-booking**: booking an appointment from Telegram on the SPEC-004 agenda. PRD `US-004`,
  `RF-005` (create), `NFR-07`, `R-05`, `CONF-001` (a), and SPEC-001 R14 (`offer_booking`);
  traceability row **SPEC-007**, a follow-up of SPEC-004.
  - **Ways in:** `/cita`, a «Pedir cita» button after price or treatment answers, and strict
    booking phrases.
  - **Flow:** type menu, up to 3 slot buttons, an explicit confirmation, a message for every
    result, and `/micita`.
  - **Where it runs:** in flow A and Neon only, never through B or Gemini, with consent required.
    B only gains `offer_booking`.
  - **Status: implemented for the demo** (2026-11-22; R0–R7 done; every acceptance criterion met
    by Node and SQL tests, 31 + 8 pinned runs and the Telegram test). Found in R6 and fixed: n8n
    drops a whole-keyboard expression in a Telegram node, so A has one node per number of
    buttons (1–5) with one expression per button field (README, "Booking (SPEC-007)"); and «Ver
    más» got its own text (`MORE_SLOTS_TEXT`, human). Example agenda data until DEP-01 and
    DEP-03, and pending DEP-04 like SPEC-006, so real patients stay blocked.
  - [clarifications](./008-booking/clarifications.md), Q1–Q15
  - [spec](./008-booking/spec.md), BK1–BK27
  - [plan](./008-booking/plan.md) — Steps 0–7
  - [tasks](./008-booking/tasks.md) — R0–R7
  - Code: [`n8n/code/citas.js`](../n8n/code/citas.js) · test `node n8n/code/citas.test.js` ·
    phrases [`evals/booking_phrases.yaml`](../evals/booking_phrases.yaml) · SQL
    [`app/infra/sql/004_booking.sql`](../app/infra/sql/004_booking.sql), tested by
    `tests/infra/test_booking_sql.py` (test branch only)
  - Workflows: A and B, in [`n8n/workflows/`](../n8n/workflows/)

- **009-move-cancel**: moving and cancelling one's own appointment from Telegram. PRD `US-005`,
  `RF-005` (move and cancel), `NFR-07`, `R-05`; traceability row **SPEC-008**, a follow-up of
  SPEC-004 and SPEC-007.
  - **Ways in:** «Cambiar» and «Anular» under `/micita`, «Ya tienes…» and «Hecho: tienes…», and
    strict change and cancel phrases. An urgency always wins.
  - **Flow:** a confirmation before every write; a minimum notice of 2 hours (example value,
    DEP-03); a move done in one transaction that keeps the old appointment if the new slot
    fails; cancelled rows kept until the normal 30-day purge; old buttons answered safely.
  - **Consent:** withdrawing keeps the appointment and offers «Anular mi cita». Cancelling and
    its confirmation are the only steps allowed without consent (legal basis pending DEP-04).
  - **Where it runs:** flow A and Neon only. B and Gemini are not involved, and B does not
    change.
  - **Status: implemented for the demo** (2026-11-23; M0–M6 done). Every acceptance criterion is
    met, through:
    - the Node tests (change phrases 23/23 and 0/22);
    - 36 SQL tests on the test branch, concurrency included;
    - `main` checked before and after;
    - 39 pinned runs;
    - the Telegram test (move, cancel, old buttons, withdrawal with an appointment).

    The minimum notice (2 hours) is example data until DEP-03. The appointment kept after a
    withdrawal is pending DEP-04, so real patients stay blocked.
  - [clarifications](./009-move-cancel/clarifications.md), Q1–Q14
  - [spec](./009-move-cancel/spec.md), MC1–MC33
  - [plan](./009-move-cancel/plan.md) — Steps 0–6
  - [tasks](./009-move-cancel/tasks.md) — M0–M6
  - Code: [`n8n/code/citas.js`](../n8n/code/citas.js) and
    [`n8n/code/consentimiento.js`](../n8n/code/consentimiento.js) · phrases
    [`evals/change_phrases.yaml`](../evals/change_phrases.yaml) · SQL
    [`app/infra/sql/005_move_cancel.sql`](../app/infra/sql/005_move_cancel.sql), tested by
    `tests/infra/test_move_cancel_sql.py` (test branch only)
  - Workflow: A, [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json);
    B unchanged

- **010-reminders**: a Telegram reminder the day before each appointment. PRD `US-006`, `RF-006`,
  `CONF-005`, `R-06`; traceability row **SPEC-009**, a follow-up of SPEC-004, SPEC-007 and
  SPEC-008.
  - **Consent:** a separate opt-in right after booking («¿Quieres que te recuerde la cita el día
    antes?»), which can be removed from «Mi cita». Withdrawing the general consent deletes the
    reminder.
  - **Data:** the chat id is encrypted (pgcrypto) in its own table, and exists only while the
    reminder is pending. The key is in the same database, a known limitation.
  - **Sending:** a new scheduled workflow C sends each reminder exactly once:
    - due 24 hours before;
    - never in quiet hours (21:00–9:00) or with less than 2 hours left;
    - a missed run is sent late only inside that window.

    The text has no appointment type. Its buttons are «Iré», «Cambiar», «Anular» and «Hablar
    con recepción».
  - **Where it runs:** A and C with Neon only. No B, no Gemini, and C saves no executions.
  - **Sending rule** (human, 2026-11-24): only a Telegram 429 is retried; a 5xx or a network
    error becomes `failed`, because the message may have been delivered. Better a missing
    reminder than a duplicate.
  - **Status: implemented for the demo** (2026-11-24; N0–N6 done), with the **real reminder
    still pending**, like the clinical review of SPEC-003. Tested through:
    - the Node tests;
    - 41 SQL tests on the test branch: the deferred trigger with the real moves and cancels,
      two claims at once, consent at sending, and the chat id wiped in every final state;
    - `main` checked before and after (N3 and N4b);
    - 38 pinned runs of A and C;
    - the Telegram test of the opt-in, «Sí» and «No», the «Mi cita» view, and removing and
      adding the reminder.

    **Pending:** the reminder actually arriving, and «Iré», «Cambiar» and «Anular» tapped from
    it. The clinic's address and the reminder settings are example data until DEP-01 and DEP-03;
    the legal basis is pending DEP-04, so real patients stay blocked.
  - [clarifications](./010-reminders/clarifications.md), Q1–Q15 and the decisions of 2026-11-24
  - [spec](./010-reminders/spec.md), RM1–RM33
  - [plan](./010-reminders/plan.md) — Steps 0–6
  - [tasks](./010-reminders/tasks.md) — N0–N6 (and N4b)
  - Code: [`n8n/code/recordatorios.js`](../n8n/code/recordatorios.js) (C) ·
    [`n8n/code/citas.js`](../n8n/code/citas.js) (A) · test `node n8n/code/recordatorios.test.js` ·
    SQL [`app/infra/sql/006_reminders.sql`](../app/infra/sql/006_reminders.sql), tested by
    `tests/infra/test_reminders_sql.py` (test branch only)
  - Workflows: A, [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json),
    and C, [`n8n/workflows/lifecenter-reminders.json`](../n8n/workflows/lifecenter-reminders.json);
    B unchanged

- **011-reception-handoff**: passing a conversation to reception through a private Telegram group,
  complaints and ratings (Phase 3). PRD `RF-007`, `RF-009`, `US-008`, `US-002`, `US-003`, `R-07`;
  traceability row **SPEC-010**.
  - **Handoff:** «Hablar con recepción» → a confirmation → the patient writes the message → it is
    posted pseudonymized in «LifeCenter Recepción» with the reason and a short code; reception
    replies to it, and the bot forwards the reply. «Cerrar», or 48 h.
  - **Complaints:** `/queja` and a strict phrase list open the same path, marked as a complaint.
  - **Ratings:** 👍/👎 after B's answers, kept only as counts per day and reason.
  - **Data:** the chat id encrypted with the SPEC-009 key in its own table, with no message text;
    the group id only in Neon (`reception_settings`); the group's auto-delete at 1 week.
  - **Where it runs:** A and Neon. B does not change; C's nodes do not change.
  - **Status: implemented for the demo** (2026-11-24; H0–H6 done), with the real `/queja` and
    rating tests still pending. Tested through:
    - the Node tests (complaint phrases 16/16 and 0/16);
    - 33 SQL tests on the test branch; `main` checked before and after (H3);
    - 20 pinned runs of A;
    - the Telegram test of a real handoff (R-U4RK): confirmation, message, the group post with its
      reason and «Cerrar», the reply forwarded to the patient, closing, and a group message ignored.

    **Pending:** `/queja` and 👍/👎 from Telegram (Gemini answered 503 during the test). The group's
    1-week auto-delete is a known limitation; real patients stay blocked until DEP-04.
  - [clarifications](./011-reception-handoff/clarifications.md), D1–D5 and P1–P15
  - [spec](./011-reception-handoff/spec.md), RH1–RH24
  - [plan](./011-reception-handoff/plan.md) — Steps 0–6
  - [tasks](./011-reception-handoff/tasks.md) — H0–H6 (and H3b)
  - Code: [`n8n/code/recepcion.js`](../n8n/code/recepcion.js) and
    [`n8n/code/consentimiento.js`](../n8n/code/consentimiento.js) · phrases
    [`evals/complaint_phrases.yaml`](../evals/complaint_phrases.yaml) · SQL
    [`app/infra/sql/007_reception.sql`](../app/infra/sql/007_reception.sql), tested by
    `tests/infra/test_reception_sql.py` (test branch only)
  - Workflow: A, [`n8n/workflows/lifecenter-telegram-demo.json`](../n8n/workflows/lifecenter-telegram-demo.json);
    B and C unchanged

Pending (not yet scaffolded): US-007's remaining parts and RF-008 (reception marks answers for the
evals), per `docs/03-prd.md` §11.

Future improvements (not specified yet):

- **Greetings and general questions** (human, 2026-11-23). Today «hola» or «¿qué haces?» go to
  B, which abstains, because the knowledge base has no answer. The bot could reply with what it
  can do: answer about prices, hours and treatments with sources; book, move and cancel an
  appointment (`/cita`, `/micita`); and talk to reception. It would be a deterministic text,
  with no Gemini, before B, in the same way as the booking phrases.
