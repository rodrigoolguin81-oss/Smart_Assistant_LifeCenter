---
type: clarifications
spec_id: SPEC-006
title: consent — Clarifications
description: Questions resolved with the human before writing SPEC-006 (explicit consent in the bot's first message, with urgencies always answered and a minimal consent record), plus the facts found, assumptions, known limitations and dependencies.
tags: [clarify, consent, SPEC-006, CONF-005, R-06, DEP-04, RES-02, NFR-08, RF-004]
status: draft
sources: [../../docs/03-prd.md, ../003-n8n-migration/spec.md, ../004-urgencies/spec.md, ../005-pseudonymized-log/spec.md, ../005-pseudonymized-log/clarifications.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-21T00:00:00Z }
verified: { by: human, at: null }
stale_after: null
---

# consent — Clarifications

Covers PRD (`docs/03-prd.md`) CONF-005 option (a), "consentimiento explícito en el primer mensaje
del bot", together with risk R-06 and dependency DEP-04. It builds on the two demo workflows of
SPEC-005: `lifecenter-telegram-demo` (A, channel, saves nothing) and `lifecenter-demo-core` (B,
core, pseudonymized executions kept 30 days). The PRD has no §11 row for this yet; the feature
takes **SPEC-006**.

## Facts found before asking (agent, 2026-11-21)

- **CONF-005 in the PRD is about reminders.** It is the conflict "send reminders to every patient"
  vs. "the patient must consent before receiving messages", written into RF-006 and US-006. This
  spec widens it to consent **before processing any conversation**. For health data the GDPR
  basis is explicit consent (art. 9.2.a). Withdrawing it must be as easy as giving it (art. 7.3),
  and the controller must be able to show it was given (art. 7.1).
- **The urgency detector lives in B** (SPEC-005 P2), and B saves its executions. Calling B to
  detect an urgency for a user without consent would store their pseudonymized message, which is
  health data, without consent. A saves nothing, except the window of about 15 minutes accepted in
  SPEC-005 (Known limitations).
- **A has a single button branch.** Every `callback_query` goes to "Confirmar botón" → "Responder
  recepción" (D8). The only button sent today carries `callback_data: "handoff"`. The consent
  buttons need their own routing.
- **Where the state could live:**
  - n8n's workflow static data is part of the workflow, so it would end up in the **public**
    exported JSON. Ruled out.
  - an n8n Data Table is local to the instance;
  - Neon is already used by B, in region `eu-central-1`.
- **An unkeyed hash of the Telegram id does not protect it.** Telegram ids are about 10 digits,
  so they can be brute-forced. A keyed hash (HMAC) needs its key outside the JSON. SPEC-005 Q2 hit
  the same problem: Code nodes cannot read n8n credentials.

## Questions & answers (human, 2026-11-21)

- Q1: Scope, id and location?
  → A: `specs/006-consent/`, `spec_id: SPEC-006`. Consent covers the **processing of
  conversations**. Reminders (RF-006) are out of scope and **will reuse this consent** later.
- Q2: Where is the consent state stored, and under which identifier?
  → A: **(a) A table in Neon** keyed by an **HMAC of the Telegram `from.id`**, computed **in
  Postgres with `pgcrypto`**. The key lives **only in Neon**, never in the workflow JSON nor in the
  repo. The raw id reaches Neon only as a query parameter and is not stored.
  - **Limitation to record:** the key and the table are in the **same database**, so whoever can
    read the database can compute the HMAC of a known id (Known limitations).
  - Rejected: (b) an n8n Data Table with the id in the clear (unnecessary personal data); (c) an
    unkeyed hash (reversible by brute force).
- Q3: What is stored?
  → A: Four fields only: `subject` (the HMAC), `status` (`accepted` or `revoked`),
  `text_version` (the version of the notice the user saw) and `decided_at`. No name, username,
  chat id or message text. **Rejections are not stored**: a user who says no leaves no record, and
  the bot shows the notice again on their next message.
- Q4: Urgencies without consent?
  → A: **(a) A runs `urgencias.js` itself, before checking consent.** An urgency always gets the
  fixed SPEC-003 reply and the "Hablar con recepción" button. **Without consent, B is not called**
  and nothing is stored. The consent notice is **not** added to the urgency reply; it goes with the
  user's **next** message.
- Q5: The message that triggered the notice?
  → A: **It is discarded.** After accepting, the bot replies «Gracias. Ya puedes escribirme tu
  consulta.» Nothing is kept before consent (Telegram's `callback_data` is limited to 64 bytes
  anyway).
- Q6: Notice text?
  → A: **Approved**, with «Esto es una demostración: no escribas datos reales.» added at the end,
  before the question. Final text:

  > Hola, soy el asistente de LifeCenter. Para responderte: quito tu nombre, teléfono, DNI y email
  > de los mensajes antes de procesarlos; envío la consulta a un modelo de IA externo (Gemini, de
  > Google), y guardo el recorrido de cada consulta, sin tus datos, durante 30 días. Si me cuentas
  > un síntoma te daré siempre el teléfono de la clínica. Esto es una demostración: no escribas
  > datos reales. ¿Aceptas?

  Buttons «Acepto» and «No acepto». **No link to a privacy policy for now** (pending DEP-04).
  The reply on rejection is **approved**: «De acuerdo, no procesaré tus consultas. Puedes llamar a
  recepción. Si cambias de opinión, escribe /privacidad.»
- Q7: Withdrawal (art. 7.3)?
  → A: A **`/privacidad`** command shows the notice and the current status, with a **«Retirar
  consentimiento»** button when consent is in force (or «Acepto» / «No acepto» when it is not).
  **Limitation to record:** executions already stored in B **cannot be deleted per user**,
  because B holds no identifier; they expire at 30 days.
- Q8: Versioning?
  → A: A **`CONSENT_TEXT_VERSION`** constant. When the notice changes, the version changes and
  everyone is asked again.
- Q9: Other cases without consent?
  → A: Agreed:
  - `/start` shows the notice;
  - «Hablar con recepción» keeps working (it involves no processing);
  - a non-text message gets the notice instead of "Pedir texto" (D12).
- Q10: How long is the consent record kept?
  → A: **(a)** An accepted record is kept **until it is withdrawn**. A withdrawn record is kept
  **30 days as proof** and then deleted.
- Q11: Code and tests?
  → A: As in SPEC-003: the consent logic and texts live in **`n8n/code/consentimiento.js`**, with a
  **Node test** (written first) and a **sync check** against the exports.
- Q12: Assumptions?
  → A: The four proposed assumptions are accepted (A1–A4 below).

## Assumptions

- **A1:** private chats only. Consent is keyed by `from.id`, the person, not by the chat.
- **A2:** team members who already used the bot are treated as new users: nobody has consented
  yet when this spec goes live.
- **A3:** the SPEC-005 window in which A's raw execution stays in n8n's local database for up to
  about 15 minutes also applies **before** consent. It is the same accepted limitation.
- **A4:** everything here is **provisional until DEP-04** (Rossana Riquelme) and does **not**
  unblock real patients.
- **A5 (agent, to be confirmed at review):** pseudonymization (SPEC-001 R4), the urgency rules and
  texts (SPEC-003) and B's behaviour do not change. B gains no consent logic: A only calls it for
  users with consent in force.

## Known limitations

- **Key and table in the same database** (Q2). The HMAC protects the id against someone who only
  sees the table or an export, not against someone with full access to the Neon database. A
  separate key store is left for production (DEP-04).
- **Executions already in B cannot be deleted per user** (Q7). After a withdrawal they remain
  until they expire at 30 days. They contain only pseudonymized text and no identifier.
- **Urgencies without consent leave no record** (Q4). A saves nothing, so they do not appear with
  `reason: urgency` (SPEC-003 U15) in B's executions. Urgencies of users with consent are still
  recorded through B.
- **Before consent, n8n still handles the raw message** for up to about 15 minutes in its local
  database (A3, SPEC-005).
- **The raw `from.id` travels to Neon** as a query parameter to compute the HMAC. It is not
  stored in the table; Neon's own query logs are not covered by this spec.
- **The withdrawn record is deleted "after 30 days plus at most the next lookup"**: the purge runs
  with the consent queries, not on a schedule (see spec).

## Dependencies and conditions

- **DEP-04:** LifeCenter's management validates the consent policy: the notice text, the record
  kept, its retention and the missing privacy-policy link. All of it is provisional until then.
- **RF-006 (reminders):** will reuse this consent. Whether consent to conversations also covers
  proactive messages is left to that spec and to DEP-04.
- **Opening to real patients stays blocked** (SPEC-005 clarifications, "Dependencies and
  conditions"). This spec resolves the consent item (CONF-005) for the demo only. The others remain
  open: the Gemini free tier, the example data and phone (DEP-01), the clinical review (SPEC-003
  U5), A's raw data in n8n's local database, the key in the same database, and DEP-04.
