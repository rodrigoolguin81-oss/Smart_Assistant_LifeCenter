---
type: spec
spec_id: SPEC-006
title: consent — Functional Spec
description: Requirements for explicit consent in the bot's first message in the n8n demo (notice, accept and reject buttons, /privacidad and withdrawal), with urgencies always answered, no processing before consent and a minimal HMAC-keyed consent record in Neon (CONF-005, R-06, DEP-04, RES-02, RF-004), in EARS notation.
tags: [spec, consent, SPEC-006, CONF-005, R-06, DEP-04, RES-02, NFR-08, RF-004]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md, ../003-n8n-migration/spec.md, ../004-urgencies/spec.md, ../005-pseudonymized-log/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-21T00:00:00Z }
verified: { by: human, at: 2026-11-21T00:00:00Z }
stale_after: null
---

# consent — Specification

Traceability: PRD `docs/03-prd.md` §10 (CONF-005, option a), §8 (R-06), §9 (DEP-04), §6 (RES-02),
§5.2 (NFR-08), §5.1 (RF-004; RF-006 reuses this later); new traceability row **SPEC-006**.
Changes the channel workflow A of SPEC-005 (`specs/005-pseudonymized-log/`); B and SPEC-003
(`specs/004-urgencies/`) are unchanged in behaviour. Decisions in
[clarifications](./clarifications.md).

## Context

Hoy el bot procesa cualquier mensaje en cuanto llega: lo seudonimiza, lo manda a B, B guarda su
recorrido 30 días y, si hace falta, lo envía a Gemini. Nadie ha aceptado nada. Esta spec añade un
paso previo en el flujo de canal: la primera vez que alguien escribe, el bot explica qué hace con
sus mensajes y le pide que acepte o rechace con botones. Hasta que acepta, ninguna consulta llega a
B. La única excepción son las urgencias: se detectan en el propio flujo de canal y se responden
siempre, con o sin consentimiento.

**Definitions.**

- *User*: the Telegram account that sent the update, identified by `from.id` (clarifications A1).
- *Subject*: `HMAC-SHA256(from.id, consent key)`, computed in Postgres with `pgcrypto`. The
  *consent key* exists only in Neon.
- *Consent record*: a row of the Neon table `consent` with exactly `subject`, `status`
  (`accepted` | `revoked`), `text_version` and `decided_at` (clarifications Q3).
- *Consent in force*: a record with `status = accepted` and `text_version =
  CONSENT_TEXT_VERSION`. Anything else (no record, `revoked`, an older version) is *no consent*.
- *Consent module*: `n8n/code/consentimiento.js`, which holds `CONSENT_TEXT_VERSION`, every text
  below and the decision logic (clarifications Q11).
- *Command*: a text message that is exactly `/start` or `/privacidad`, optionally followed by
  `@<bot name>`, ignoring surrounding spaces and **letter case** (`/Privacidad`, `/PRIVACIDAD`;
  human, 2026-11-22, because phone keyboards often capitalize the first letter). A command
  followed by other text is not a command.

**Fixed texts.**

- `CONSENT_NOTICE` (approved by the human, 2026-11-21):
  «Hola, soy el asistente de LifeCenter. Para responderte: quito tu nombre, teléfono, DNI y email
  de los mensajes antes de procesarlos; envío la consulta a un modelo de IA externo (Gemini, de
  Google), y guardo el recorrido de cada consulta, sin tus datos, durante 30 días. Si me cuentas un
  síntoma te daré siempre el teléfono de la clínica. Esto es una demostración: no escribas datos
  reales. ¿Aceptas?»
  Buttons: «Acepto» and «No acepto».
- `ACCEPTED_TEXT` (approved, 2026-11-21): «Gracias. Ya puedes escribirme tu consulta.»
- `REJECTED_TEXT` (approved, 2026-11-21): «De acuerdo, no procesaré tus consultas. Puedes llamar a
  recepción. Si cambias de opinión, escribe /privacidad.»
- **Proposed by the agent and approved by the human, 2026-11-21:**
  - `REVOKED_TEXT`: «He retirado tu consentimiento. No procesaré más consultas tuyas. Si cambias
    de opinión, escribe /privacidad.»
  - `STATUS_ACCEPTED`, appended to the notice in `/privacidad`: «Estado: aceptaste este aviso el
    {dd/mm/aaaa}.» Button: «Retirar consentimiento».
  - `STATUS_NONE`, appended to the notice in `/privacidad`: «Estado: no has aceptado este aviso.»
    Buttons: «Acepto» and «No acepto».
  - If the consent lookup fails: the CHG-001 D7 error text, «Ahora mismo no puedo responder.
    ¿Quieres que pase tu consulta a recepción?», with the «Hablar con recepción» button.

## Requirements (EARS)

### Order of checks in A (clarifications Q4, Q9)

- C1. WHEN a text message that is not a command arrives, A SHALL pseudonymize it ("Seudonimizar",
  unchanged) and run the SPEC-003 urgency detector on the pseudonymized text **before** looking up
  consent.
- C2. IF the level is `urgent` or `severe` AND there is no consent in force, THEN A SHALL reply
  with the SPEC-003 urgency reply (U11: fixed text, example-phone notice and «Hablar con
  recepción») and SHALL NOT call B. The reply SHALL NOT include the consent notice.
- C3. WHEN there is consent in force, A SHALL handle every text message that is not a command
  exactly as in SPEC-005, calling B with `question` only. Urgencies of these users are therefore
  still recorded by B (SPEC-003 U15).
- C4. IF the level is `none` AND there is no consent in force, THEN A SHALL reply with
  `CONSENT_NOTICE` and its buttons, SHALL NOT call B, and SHALL discard the message (clarifications
  Q5).
- C5. WHEN a message without text arrives (D12) AND there is no consent in force, A SHALL reply
  with `CONSENT_NOTICE` and its buttons instead of the D12 text. With consent in force, D12 applies
  unchanged.
- C6. IF the consent lookup fails (Neon error or timeout), THEN A SHALL reply with the D7 error
  text and the «Hablar con recepción» button, SHALL NOT call B and SHALL store nothing. Because of
  C1, an urgency is still answered with the urgency reply.

### Buttons (clarifications Q3, Q5, Q7, Q8)

- C7. Every button A sends SHALL carry a `callback_data` of at most 64 bytes that names its action
  (`handoff`, accept, reject or withdraw). The accept and reject buttons SHALL also carry the
  `CONSENT_TEXT_VERSION` they were shown with.
- C8. WHEN the user taps «Acepto» with the current version, A SHALL write a consent record with
  `status = accepted`, that version and `decided_at = now()`, replacing any earlier record of the
  same subject, and SHALL reply with `ACCEPTED_TEXT`.
- C9. WHEN the user taps «No acepto», A SHALL reply with `REJECTED_TEXT` and SHALL write nothing.
  An existing `revoked` record SHALL be left as it is.
- C10. WHEN the user taps «Retirar consentimiento», A SHALL set the subject's record to `status =
  revoked` with `decided_at = now()` and SHALL reply with `REVOKED_TEXT`.
- C11. IF the user taps «Acepto» or «No acepto» shown with an older version, THEN A SHALL write
  nothing and SHALL reply with the current `CONSENT_NOTICE` and its buttons.
- C12. WHEN the user taps «Hablar con recepción», A SHALL reply with the D8 text, with or without
  consent (unchanged).
- C13. A SHALL answer every button tap to Telegram (`answerCallbackQuery`), as "Confirmar botón"
  does today.

### Commands (clarifications Q7, Q9)

- C14. WHEN `/start` arrives AND there is no consent in force, A SHALL reply with
  `CONSENT_NOTICE` and its buttons.
- C15. WHEN `/privacidad` arrives, or `/start` arrives with consent in force (approved by the
  human, 2026-11-21), A SHALL reply with
  `CONSENT_NOTICE` followed by `STATUS_ACCEPTED` and «Retirar consentimiento» if there is consent in
  force, or by `STATUS_NONE` and «Acepto» / «No acepto» otherwise.
- C16. Commands SHALL NOT be pseudonymized, run through the urgency detector or sent to B.

### Consent record (clarifications Q2, Q3, Q10)

- C17. The table `consent` SHALL hold only `subject`, `status`, `text_version` and `decided_at`.
  It SHALL hold no `from.id`, chat id, name, username or message text, and SHALL hold no record of
  a rejection.
- C18. The subject SHALL be computed in Postgres with `pgcrypto` from `from.id` passed as a query
  parameter and the consent key read inside the database. The `from.id` SHALL NOT appear in any
  stored row, and the key SHALL NOT appear in any workflow, export, repo file or agent output.
- C19. The consent key SHALL be generated inside Neon by a one-off setup step that never prints
  it. The setup step SHALL be in the repo; the key SHALL NOT.
- C20. An `accepted` record SHALL be kept until it is withdrawn. A `revoked` record SHALL be
  deleted once its `decided_at` is more than 30 days old. The deletion SHALL run with the consent
  queries, so no scheduled workflow is added.
- C21. A SHALL keep its SPEC-005 settings: it saves no executions of any kind. Everything A
  passes to B SHALL stay as in SPEC-005 P5: `question` only, with no subject and no consent data.

### Versioning (clarifications Q8)

- C22. `CONSENT_TEXT_VERSION` SHALL be defined once, in the consent module. WHEN it changes, every
  existing record SHALL stop counting as consent in force, so every user sees the new notice on
  their next message.

### Code and tests (clarifications Q11)

- C23. The consent texts, the version, the parsing of commands and `callback_data`, and the
  decision of what to do for each kind of update and consent state SHALL live in
  `n8n/code/consentimiento.js`. The consent Code node(s) in A SHALL carry exactly that code, plus
  only the n8n input and output wiring.
- C24. A Node test SHALL cover, before the module is written: every decision of C2–C16, the
  texts, the 64-byte limit of C7, the command parsing and the version rule of C22.
- C25. The sync checks SHALL compare `consentimiento.js` with A's export, and `urgencias.js` with
  **both** A's and B's exports.

### Exports and documentation

- C26. A SHALL be re-exported to `n8n/workflows/` with no secret, no personal data and no
  consent key, following the SPEC-005 procedure (`shared` block removed).
- C27. The README "Demo" section SHALL describe the consent step, `/privacidad`, the one-off
  setup step of the table and key, and the limitations of this spec.

## Acceptance criteria

Tested from Telegram with a team account that has no consent record (clarifications A2).

- [ ] "¿Cuánto cuesta una limpieza?" → `CONSENT_NOTICE` with «Acepto» and «No acepto»; no new B
  execution.
- [ ] «No acepto» → `REJECTED_TEXT`; the `consent` table has no record for the account.
- [ ] "me sangra mucho la encía desde ayer" without consent → the SPEC-003 urgent reply with the
  button and no notice; no new B execution. The next message → `CONSENT_NOTICE`.
- [ ] A sticker without consent → `CONSENT_NOTICE`. «Hablar con recepción» without consent → the
  D8 text.
- [ ] «Acepto» → `ACCEPTED_TEXT`; the table has one `accepted` row with the current version.
  "¿Cuánto cuesta una limpieza?" again → 60 € with TAR-001 and both notices, and one new B
  execution containing only `question`.
- [ ] With consent, the SPEC-003 urgent and severe messages → their replies, recorded in B with
  `reason: urgency`.
- [ ] `/privacidad` → the notice, `STATUS_ACCEPTED` and «Retirar consentimiento». Tapping it →
  `REVOKED_TEXT`, the row becomes `revoked`, and the next message → `CONSENT_NOTICE`.
- [ ] A scan of the `consent` table and of A's export finds no `from.id`, chat id, profile name,
  username or key. The key is in no repo file.
- [ ] A synthetic `revoked` row dated more than 30 days ago is gone after the next consent
  lookup; a synthetic one dated less than 30 days ago remains.
- [ ] `node n8n/code/consentimiento.test.js` and `node n8n/code/urgencias.test.js` are green,
  with the sync checks against the exports.
- [ ] A is re-exported with no secret or personal data and still shows its "save no executions"
  settings. B is unchanged.

## Known limitations

- **The HMAC key is in the same database as the consent records** (accepted by the human for the
  demo, 2026-11-22). Anyone with full access to the Neon database can compute the subject of a
  known Telegram id. In production the key would live outside the database (DEP-04).
- The other limitations are listed in the [clarifications](./clarifications.md), "Known
  limitations".

## Out of scope

- Reminders and any proactive message (RF-006); they will reuse this consent.
- A privacy-policy link and the controller's legal details (DEP-04).
- Deleting a user's executions already stored in B (clarifications, Known limitations).
- A separate key store, key rotation, and Neon's own query logs.
- Group chats (clarifications A1).
- Changes to pseudonymization (SPEC-001 R4), to the urgency rules and texts (SPEC-003) or to B.
