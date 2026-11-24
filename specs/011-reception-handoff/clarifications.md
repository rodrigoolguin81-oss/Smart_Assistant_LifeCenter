---
type: clarifications
spec_id: SPEC-010
title: reception handoff, complaints and ratings — Clarifications
description: Phase 3 with a minimal scope — «Hablar con recepción» and /queja publish a pseudonymized message with a reason and a short code in a private Telegram group «LifeCenter Recepción», reception answers by replying to it and the bot forwards the answer to the patient; the chat id encrypted in its own table, deleted at closing or after 48 h; 👍/👎 after B's answers stored only as daily counts. The agent's proposals are written in; five decisions are left to the human.
tags: [clarifications, reception, handoff, complaints, ratings, SPEC-010, RF-007, RF-009, US-008, US-002, US-003]
status: verified
sources: [../../docs/03-prd.md, ../../docs/01-charter.md, ../index.md, ../010-reminders/spec.md, ../006-consent/spec.md, ../005-pseudonymized-log/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-24T00:00:00Z }
verified: { by: human, at: 2026-11-24T00:00:00Z }
stale_after: null
---

# reception handoff, complaints and ratings — Clarifications

## Number and folder

**SPEC-010**, folder `specs/011-reception-handoff/` (the next free number; folders run one ahead
of the spec ids since SPEC-002).

## What the PRD, the charter and the earlier specs say

- **RF-007:** offer «hablar con una persona» at any time, and show the handed-off conversations
  (urgencies, complaints, questions without an answer) in the reception panel.
- **RF-009 / US-008:** detect complaints, never try to resolve them, confirm that they were passed
  on, and mark them as a complaint for reception.
- **US-002 / US-003:** an abstention and an urgency offer to pass the question to reception.
- **R-07 / charter §6:** keep the phone and «hablar con una persona», and ask patients for
  feedback.
- **RF-008** (reception marks answers right or wrong for the evals) and **US-007** (the
  pseudonymized log) are not in this phase: US-007 is SPEC-005, RF-008 is a follow-up.
- **Today:** «Hablar con recepción» (`handoff`) answers with the fixed D8 text («Ahora mismo no
  puedo pasar tu consulta automáticamente. Llama a recepción…»), before consent. B returns
  `offer_handoff`, and A draws the button.
- **SPEC-009** set the pattern for the chat id: encrypted with pgcrypto in its own table, wiped as
  soon as it is not needed, never in logs or executions.
- **Human, 2026-11-24:** a private group «LifeCenter Recepción» exists, with the bot as
  administrator. Its id is never written in the chat or in the repo.

## Scope (human, 2026-11-24)

In:

1. **Handoff:** «Hablar con recepción» → a confirmation → the pseudonymized message, the reason
   (urgency, abstention, request, complaint) and a short code, posted in the group. Reception
   replies to that message in the group, and the bot forwards the reply to the patient.
2. **Complaints:** `/queja` opens the same path, marked as a complaint.
3. **Ratings:** 👍/👎 after B's answers, stored only as counts per day and reason, with no
   subject and no chat id.
4. Consent required; an urgency always wins; B does not change, or only the minimum.

Out: the web reception panel (the group replaces it for the demo), RF-008, free-text complaint
detection beyond a strict list, a conversation thread with several turns, WhatsApp, and
reception's working hours.

## Proposals written into the spec

- **P1. What is posted.** After the confirmation, the bot asks the patient to write the message
  for reception, and posts that message pseudonymized (SPEC-005 rules), not the earlier question.
  Nothing is stored before the patient confirms, and no question is kept per patient. *(Decision
  D1 below.)*
- **P2. The reason comes from where the button was shown**, so B does not change: A already
  knows B's `reason` (`abstained`, `urgency`…) when it draws the keyboard. The callback becomes
  `handoff:a` (abstention), `handoff:u` (urgency), `handoff:p` (any other button: request) and
  `handoff:q` (complaint). The old `handoff` is read as `handoff:p`.
- **P3. The code** is 4 characters from an alphabet without look-alikes (no 0/O, 1/I/L), with a
  prefix: `R-7KQ3` (handoff) or `Q-7KQ3` (complaint). It is unique among open handoffs.
- **P4. The group message**, fixed text: `[R-7KQ3] Motivo: abstención` + a blank line + the
  pseudonymized message + «Responde a este mensaje para contestar al paciente.» No name, no
  Telegram user, no appointment.
- **P5. Matching a reply:** by the group message id stored with the handoff
  (`reply_to_message.message_id`), not by parsing the code. Only replies in the registered group,
  to a message sent by the bot, count.
- **P6. Forwarding:** «Recepción de LifeCenter (R-7KQ3): …» + the reply text, to the patient. The
  reply is not stored. Several replies are allowed while the handoff is open.
- **P7. Closing:** a «Cerrar» button on the group message, or 48 h after opening. Closing deletes
  the row (and so the encrypted chat id). A reply to a closed handoff gets, in the group,
  «Esta consulta ya está cerrada.» *(Decision D3.)*
- **P8. Storage:** a table `reception_handoffs` with the code, the reason, the chat id encrypted
  with the SPEC-009 helpers (`agenda_chat_encrypt` / `agenda_chat_decrypt`, same `reminder_key`),
  the group message id, the status (`awaiting_text`, `open`) and the times. **No message text, no
  subject.** A handoff waiting for the patient's text expires after 30 minutes. *(Decision D4.)*
- **P9. Purge:** every handoff function purges expired rows, and C's `reminder_claim_due` calls
  the same purge every 15 minutes (SQL only; C's nodes do not change).
- **P10. Consent:** the new handoff needs consent in force. Without it, «Hablar con recepción»
  keeps today's D8 text, and `/queja` gets «Para pasar tu queja a recepción necesito tu
  consentimiento…» with the phone. An urgency is always answered first, with or without consent.
- **P11. Urgency wins:** if the text the patient writes for reception is an urgency, the bot
  sends the urgency reply first, and the group message is marked «urgencia» whatever the button
  said.
- **P12. Complaints:** `/queja`, and a strict phrase list («quiero poner una queja», «quiero
  hacer una reclamación», «hoja de reclamaciones»…) in A, tested with a YAML file like the booking
  phrases. A phrase never posts by itself: it opens the `/queja` confirmation. The bot never
  argues with or answers the complaint.
- **P13. Groups:** A ignores every update from a non-private chat, except replies and «Cerrar»
  in the registered group. It never sends the consent notice to a group. *(See the warning
  below.)*
- **P14. Ratings:** two buttons «👍» and «👎» under B's answered replies (`reason: answered`), not
  under abstentions, urgencies or errors. A tap adds 1 to `feedback_daily(day, reason, up, down)`,
  answers «Gracias por tu valoración.» and removes the buttons from that message, so a second tap
  is not counted. The counts have no subject and no chat id, so they need no consent of their own
  and are kept as aggregates (no purge).
- **P15. B:** no change. The reason codes and the rating buttons are built in A.

## Decisions (human, 2026-11-24)

- **D1 (a):** the patient writes a new message after confirming; nothing is stored beforehand.
- **D2 (a):** the group id lives in `reception_settings` in Neon `main`, filled by the human with
  a hidden-prompt script. Never in the repo, an export, a log or the chat.
- **D3 (a):** «Cerrar» on the group message, and closing after 48 h.
- **D4 (a):** the chat id is encrypted with `reminder_key` and the SPEC-009 helpers.
- **D5 (a):** the group's auto-delete timer is set to **1 week**. It is a known limitation and a
  setup step in the README.
- P1–P15 are accepted as written. The human will not write in the group until this spec is
  implemented.

## Decisions asked (for the record)

- **D1. What reaches reception:** (a) the patient writes a new message after confirming
  (proposed: nothing stored beforehand); or (b) the question that produced the button, which
  means keeping every pseudonymized question with its encrypted chat id for 30 minutes, even when
  nobody taps the button.
- **D2. Where the group id lives** (never in the repo or the chat):
  - (a) **proposed:** a one-row table `reception_settings` in Neon `main`, filled by you with a
    small script that asks for the id with a hidden prompt (`getpass`) and inserts it; A reads it
    in its queries. You get the id from Telegram Web: open the group, and the number after `#` in
    the address bar is the id (it starts with `-100`);
  - (b) an n8n Variable (`$vars`), if your n8n plan has Variables;
  - (c) an environment variable of the n8n process (`$env`), which needs
    `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` and so exposes every environment variable to the Code
    nodes. Not recommended.

  An n8n credential cannot be read from an expression, so it does not fit.
- **D3. Closing:** (a) «Cerrar» button + 48 h (proposed); or (b) closed automatically after the
  first reply.
- **D4. Encryption key:** (a) reuse `reminder_key` and the SPEC-009 helpers (proposed: one key for
  chat ids, one limitation); or (b) a separate `handoff_key`.
- **D5. The group history:** the pseudonymized messages stay in the Telegram group, outside the
  30-day purge. (a) Turn on the group's auto-delete (Telegram, e.g. 1 week) and record it as a
  limitation (proposed); or (b) the bot deletes its group message when the handoff closes (it can,
  as administrator, within 48 h).

## Assumptions

- A1. The group is a supergroup and the bot is an administrator, so it receives every message.
- A2. Reception answers in the group within working hours; the bot says so to the patient.
- A3. Reception staff are not patients: their messages in the group are never treated as patient
  messages, and their Telegram ids are never stored.

## Known limitations (expected)

- The group shows reception's members to each other, and Telegram keeps the group history for
  up to 1 week (the auto-delete timer, D5), outside the 30-day purge of B.
- The encryption key is in the same database as the chat ids (as in SPEC-009).
- A patient's handoffs are found by decrypting every stored chat id and comparing (no subject is
  stored). This is fine with few rows, all deleted within 48 hours; with many it would need a keyed
  hash column (human, 2026-11-24).
- The pseudonymized text can still contain a name written in other words, and health data, as in
  SPEC-005.
- The ratings say nothing about which answer was rated.

## Warning (now)

The bot is already an administrator of the group, and A is published. **A treats every message
in the group as a patient message today**: it would answer in the group with the consent notice,
and a staff member's «Acepto» would store a consent. Until this spec is implemented, do not write
in the group, or remove the bot from it.

## Dependencies and conditions

- DEP-04 (consent, pseudonymization and retention policy) also covers what reaches the group.
  Real patients stay blocked.
- SPEC-005 (pseudonymization), SPEC-006 (consent), SPEC-003 (urgency) and SPEC-009 (chat id
  encryption) are reused, not changed.
