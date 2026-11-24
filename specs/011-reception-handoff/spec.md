---
type: spec
spec_id: SPEC-010
title: reception handoff, complaints and ratings — Functional Spec
description: Requirements for passing a conversation to reception through a private Telegram group (RF-007, US-002, US-003), complaints by /queja and a strict phrase list (RF-009, US-008), and 👍/👎 ratings after B's answers kept only as daily counts — consent required, urgency first, the chat id encrypted in its own table and deleted at closing or after 48 h, no message text stored, B unchanged. EARS notation.
tags: [spec, reception, handoff, complaints, ratings, SPEC-010, RF-007, RF-009, US-008, SPEC-005, SPEC-006, SPEC-009]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md, ../010-reminders/spec.md, ../006-consent/spec.md, ../005-pseudonymized-log/spec.md, ../004-urgencies/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-24T00:00:00Z }
verified: { by: human, at: 2026-11-24T00:00:00Z }
stale_after: null
---

# reception handoff, complaints and ratings — Specification

Written with the agent's proposals (clarifications P1–P15) and the human's decisions of
2026-11-24 (D1–D5, option a each).

## Glossary

- *Reception group*: the private Telegram group «LifeCenter Recepción». Its id lives only in the
  place chosen in D2 (proposed: `reception_settings` in Neon).
- *Handoff*: a row of `reception_handoffs`: code, reason, encrypted chat id, group message id,
  status (`awaiting_text` or `open`), times. No message text, no subject.
- *Reason*: `urgencia`, `abstención`, `petición` or `queja`.

## Requirements (EARS)

### Handoff (RF-007; D1, D3)

- RH1. WHEN a patient with consent in force taps «Hablar con recepción», A SHALL reply with
  `HANDOFF_CONFIRM_TEXT` and the buttons «Sí, pasar a recepción» and «No».
- RH2. The button SHALL carry the reason: `handoff:a` under an abstention, `handoff:u` under an
  urgency, `handoff:p` anywhere else; the old `handoff` SHALL be read as `handoff:p`. B SHALL
  not change.
- RH3. WHEN the patient confirms, A SHALL create a handoff in `awaiting_text` with a new code and
  the encrypted chat id, and reply with `HANDOFF_WRITE_TEXT`. (D1 a)
- RH4. WHEN a patient with a handoff in `awaiting_text` sends a text, A SHALL pseudonymize it
  (SPEC-005), run the urgency detector, post `GROUP_MESSAGE` in the reception group, store the
  group message id, set the handoff `open`, and reply with `HANDOFF_SENT_TEXT`. The text SHALL not
  be stored anywhere.
- RH5. IF that text is an urgency, THEN A SHALL first send the SPEC-003 urgency reply, and the
  group message SHALL say `urgencia`.
- RH6. A handoff in `awaiting_text` SHALL expire after 30 minutes. «No» SHALL create nothing and
  reply with `HANDOFF_CANCELLED_TEXT`.
- RH7. IF a patient without consent in force taps «Hablar con recepción», THEN A SHALL keep
  today's D8 text, and nothing SHALL be stored.
- RH8. IF posting in the group fails, THEN A SHALL delete the handoff and reply with
  `HANDOFF_FAILED_TEXT` (the phone).

### Reception's reply (RF-007; D3)

- RH9. WHEN a message in the reception group replies to a group message of an `open` handoff, A
  SHALL send `RECEPTION_REPLY_TEXT` with the reply text to the patient (decrypted chat id), and
  SHALL store nothing of the reply.
- RH10. WHEN «Cerrar» is tapped on a group message, the handoff SHALL be deleted, and A SHALL
  edit the group message to show «Cerrada». A handoff SHALL also be deleted 48 hours after it was
  opened. (D3 a)
- RH11. IF a reply concerns a closed or unknown handoff, THEN A SHALL answer in the group with
  `HANDOFF_CLOSED_TEXT` and send nothing to any patient.
- RH12. A SHALL ignore every update from a chat that is not private, except replies and «Cerrar»
  in the reception group. It SHALL never send the consent notice, or any patient text, to a
  group, and SHALL never store a reception member's id.

### Complaints (RF-009, US-008)

- RH13. WHEN a patient with consent sends `/queja`, or a text matching the strict complaint list
  (`evals/complaint_phrases.yaml`), A SHALL reply with `COMPLAINT_CONFIRM_TEXT` and the buttons
  «Sí, pasar a recepción» (`handoff:q`) and «No». From there the path SHALL be RH3–RH11, with the
  reason `queja` and the code prefix `Q-`.
- RH14. The bot SHALL never argue with, answer or judge a complaint. An urgency in the text SHALL
  win (RH5).
- RH15. IF the patient has no consent, THEN `/queja` and a complaint phrase SHALL get
  `COMPLAINT_NO_CONSENT_TEXT` (the phone), and nothing SHALL be stored.

### Ratings (R-07)

- RH16. A SHALL add «👍» and «👎» under B's replies with `reason: answered`, and only those, on two
  rows (human, 2026-11-24).
- RH17. WHEN one is tapped, A SHALL add 1 to `feedback_daily(day Madrid, reason, up, down)`,
  reply with `RATING_THANKS_TEXT`, and remove the two buttons from that message. Nothing else
  SHALL be stored: no subject, no chat id, no text.
- RH18. The rating buttons SHALL need consent in force; without it they SHALL count nothing and
  get the consent notice.

### Data and privacy (SPEC-005, SPEC-009; D2, D4, D5)

- RH19. The chat id SHALL be stored only in `reception_handoffs`, encrypted with the SPEC-009
  helpers and `reminder_key` (D4 a), and SHALL be deleted with the row. No function SHALL return
  it outside the forwarding.
- RH20. Every handoff function SHALL purge expired rows; C's `reminder_claim_due` SHALL call the
  same purge (SQL only; C's nodes do not change).
- RH21. Withdrawing consent SHALL delete the patient's handoffs.
- RH22. The reception group id SHALL live only in `reception_settings` in Neon (D2 a). It SHALL
  never be in the repo, an export, a log or the chat.
- RH23. A and C SHALL save no executions; B SHALL receive only `question`, as today.
- RH24. The group's auto-delete timer SHALL be set to 1 week by the human (D5 a), recorded as a
  limitation and as a setup step in the README.

## Fixed texts (proposed)

- `HANDOFF_CONFIRM_TEXT`: «¿Quieres que pase tu consulta a recepción? Te pediré que la escribas
  en un mensaje; la leerán sin tu nombre ni tu teléfono.»
- `HANDOFF_WRITE_TEXT`: «Escribe en un mensaje lo que quieres que lea recepción. No incluyas datos
  personales.»
- `HANDOFF_SENT_TEXT`: «Hecho. He pasado tu consulta a recepción (código {codigo}). Te responderán
  por aquí en horario de la clínica.»
- `HANDOFF_CANCELLED_TEXT`: «De acuerdo, no paso nada a recepción.»
- `HANDOFF_FAILED_TEXT`: «Ahora mismo no puedo pasar tu consulta. Llama a recepción en horario de
  atención.»
- `GROUP_MESSAGE`: «[{codigo}] Motivo: {motivo}» + blank line + the pseudonymized text + blank
  line + «Responde a este mensaje para contestar al paciente.», with the button «Cerrar».
- `RECEPTION_REPLY_TEXT`: «Recepción de LifeCenter ({codigo}): {texto}»
- `HANDOFF_CLOSED_TEXT`: «Esta consulta ya está cerrada.»
- `COMPLAINT_CONFIRM_TEXT`: «Siento lo ocurrido. ¿Quieres que pase tu queja a recepción? Te pediré
  que la escribas en un mensaje; la leerán sin tu nombre ni tu teléfono.»
- `COMPLAINT_NO_CONSENT_TEXT`: «Para pasar tu queja a recepción necesito tu consentimiento
  (/privacidad). También puedes llamar a recepción en horario de atención.»
- `RATING_THANKS_TEXT`: «Gracias por tu valoración.»

## Acceptance criteria

- [ ] Node tests: the reason in each handoff button; the code alphabet and prefixes; the strict
  complaint list (true and false cases, urgency wins); the group message has no name, phone or
  user; the rating buttons only under `answered`; every callback ≤ 64 bytes.
- [ ] SQL tests on the test branch: the chat id encrypted and deleted at closing, at 48 h, at
  30 min in `awaiting_text` and on withdrawal; codes unique among open handoffs; a reply to a
  closed handoff finds nothing; `feedback_daily` has no subject or chat id column; re-applying the
  schema changes nothing else.
- [ ] Pinned runs of A: confirm, «No», write, urgency in the text, posting failure, reception
  reply, «Cerrar», reply after closing, a message from another group, a staff message in the
  group, `/queja` with and without consent, a complaint phrase, 👍 and 👎.
- [ ] `main` checked before and after; A and C save no executions; B unchanged.
- [ ] Telegram test: a handoff and a complaint answered from the group, «Cerrar», and a rating.

## Out of scope

The web reception panel, RF-008, multi-turn threads, reception hours, free complaint detection,
WhatsApp, and any change to B.
