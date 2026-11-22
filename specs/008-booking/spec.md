---
type: spec
spec_id: SPEC-007
title: booking — Functional Spec
description: Requirements for booking an appointment from Telegram on the SPEC-004 agenda (US-004, RF-005 create, NFR-07) — /cita, the «Pedir cita» button (offer_booking), strict free-text phrases, the type menu, slot buttons, an explicit confirmation, a message for every result, /micita — all in flow A and Neon, never through B or Gemini, with consent required. EARS notation.
tags: [spec, booking, SPEC-007, US-004, RF-005, NFR-07, CONF-001, SPEC-004, SPEC-006, SPEC-001]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md, ../007-agenda/spec.md, ../006-consent/spec.md, ../005-pseudonymized-log/spec.md, ../004-urgencies/spec.md, ../002-answer-generation/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# booking — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-004), §5.1 (RF-005, create only), §5.2 (NFR-07), §8
(R-05), §10 (CONF-001, option a); SPEC-001 R14 (`offer_booking`). It builds on SPEC-004
(`specs/007-agenda/`), SPEC-006 (`specs/006-consent/`), SPEC-005 (`specs/005-pseudonymized-log/`)
and SPEC-003 (`specs/004-urgencies/`). Decisions in [clarifications](./clarifications.md).

## Context

Hoy el bot responde preguntas, pero no da citas. La agenda ya existe en Neon (SPEC-004) y sabe
buscar huecos y reservar sin dobles reservas, pero nadie la usa. Esta spec permite pedir cita
desde Telegram:

- de tres formas:
  - escribiendo `/cita`;
  - pulsando «Pedir cita» bajo una respuesta sobre un precio o un tratamiento;
  - escribiendo una frase clara como «quiero pedir cita»;
- el bot pregunta el tipo, enseña hasta 3 huecos con botones, repite fecha, hora y tipo, y solo
  reserva cuando el paciente confirma.

Todo ocurre en el flujo de canal A y en Neon: B y Gemini no intervienen. Mover y anular la cita,
los recordatorios y el panel de recepción vienen después.

**Definitions.**

- *Booking step*: any update handled by this spec: the `/cita` or `/micita` command, a button
  whose `callback_data` starts with `bk:`, a booking phrase, or the «Pedir cita» button.
- *Command*: as in SPEC-006. The message is exactly `/cita` or `/micita`, optionally followed by
  `@<bot>`. Surrounding spaces and letter case are ignored.
- *Booking phrase*: a pseudonymized text that matches the fixed, strict phrase list of the
  booking module (Q2).
- *Bookable type* / *request-only type*: as in SPEC-004.
  - Bookable: `revision`, `limpieza` and `primera_visita`.
  - Request only: `blanqueamiento` and `tratamiento_largo`.
- *Slot code*: a slot's start as minutes since the Unix epoch, in base 36.
- *Booking callbacks*, each at most 64 bytes:

  | `callback_data` | Meaning |
  |---|---|
  | `bk:menu` | open the type menu («Pedir cita») |
  | `bk:t:<type>` | choose a type |
  | `bk:o` | «Otro tratamiento» |
  | `bk:s:<type>:<slot>` | choose a slot |
  | `bk:c:<type>:<slot>` | confirm |
  | `bk:m:<type>:<slot>` | «Ver más», after that slot |
  | `bk:r:<type>` | «Elegir otro hueco» |

- *Booking module*: `n8n/code/citas.js`. It holds the texts, the callback codec, the phrase
  detector, the date formatting and the booking decisions.
- *Madrid date*: the date and time in Europe/Madrid.
  - Button labels are short («lun 7 dic · 9:00»).
  - Texts spell the date out in full («lunes 7 de diciembre», «9:00»).
  - The year is added only when it is not the current one.

**Fixed texts.** The texts approved by the human (clarifications Q3, Q4, Q6, Q9, Q10;
2026-11-22) are:

- `REQUEST_ONLY_TEXT`: «Ese tratamiento necesita una valoración previa en la clínica. Puedo
  reservarte una primera visita, o puedes hablar con recepción.» Buttons «Primera visita» ·
  «Hablar con recepción».
- `SLOTS_TEXT`: «Estos son los primeros huecos para {tipo}:», with the slot buttons, «Ver más» and
  «Hablar con recepción».
- `NO_SLOTS_TEXT`: «Ahora mismo no hay huecos libres para {tipo} en los próximos 30 días. Llama a
  recepción para buscar otra fecha.» Button «Hablar con recepción».
- `CONFIRM_TEXT`: «Vas a reservar {tipo} el {fecha} a las {hora}. ¿Lo confirmo?» Buttons
  «Confirmar» · «Elegir otro hueco».
- `BOOKED_TEXT`: «Hecho: tienes {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, de
  momento llama a recepción.»
- `TAKEN_TEXT`: «Ese hueco se acaba de ocupar. Estos son los siguientes:», with the slot buttons.
- `UNAVAILABLE_TEXT`: «Ese hueco ya no está disponible. Estos son los siguientes:», with the slot
  buttons.
- `LIMIT_TEXT`: «Ya tienes {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, llama a
  recepción.» The human changed it at the R1 review (2026-11-22), so it reads «Ya tienes una
  limpieza el lunes 7 de diciembre a las 9:00…».
- `MY_APPOINTMENT_TEXT`: «Tu próxima cita: {tipo} el {fecha} a las {hora}. Para cambiarla o
  anularla, llama a recepción.»
- `NO_APPOINTMENT_TEXT`: «No tienes ninguna cita reservada. Escribe /cita para pedir una.»
- On a Neon failure, the CHG-001 D7 text with «Hablar con recepción».

**{tipo} in every text** is the type with its article, taken from the type code («una limpieza»,
«una revisión», «una primera visita»). This includes `LIMIT_TEXT` and `MY_APPOINTMENT_TEXT`
(«Tu próxima cita: una limpieza el…»), as decided by the human at the R1 review (2026-11-22).

**Extra buttons, approved by the human at the R1 review (2026-11-22):**

- «Hablar con recepción» is on every booking message except the confirmation, which keeps only
  «Confirmar» and «Elegir otro hueco».
- `NO_APPOINTMENT_TEXT` also gets «Pedir cita».

**Proposed by the agent and approved by the human (2026-11-22):**

- `TYPE_MENU_TEXT`: «¿Qué tipo de cita quieres?» Buttons «Revisión» · «Limpieza» · «Primera
  visita» · «Otro tratamiento» · «Hablar con recepción».
- Button labels «Pedir cita», «Ver más», «Confirmar» and «Elegir otro hueco».

## Requirements (EARS)

### Ways in and order (clarifications Q2, Q8, Q14)

- BK1. WHEN `/cita` arrives with consent in force, A SHALL start the booking flow (BK9). IF the
  patient already has a future appointment, THEN it SHALL reply with `LIMIT_TEXT` instead
  (BK16).
- BK2. WHEN a text message arrives, A SHALL check, in this order:
  1. the urgency (SPEC-003);
  2. consent (SPEC-006);
  3. whether it is a booking phrase;
  4. only then send it to B.

  An urgency SHALL always win: «me duele una muela, quiero cita» gets the urgency reply.
  - With consent in force, the phrase check SHALL be skipped when «Detectar urgencia» found
    `urgent` or `severe`. The message then goes to B, which answers and records the urgency
    (SPEC-003 U15).
  - This is checked by a Node test with mixed messages, such as «quiero cita, me sangra mucho la
    encía» and «necesito una cita urgente, se me ha hinchado la cara» (human, 2026-11-22).
- BK3. The booking phrase list SHALL be fixed and strict (clarifications, Decisions Q2).
  - Only clear requests SHALL match, such as «quiero pedir cita», «¿puedo reservar una
    limpieza?» or «dame cita para una revisión».
  - Mentions of an existing appointment, questions about price, and requests to move or cancel
    SHALL NOT match, and SHALL keep going to B as today. Examples: «tengo una cita el lunes»,
    «¿cuánto cuesta una cita?», «cancelar mi cita», «cambiar mi cita».
- BK4. WHEN a booking phrase matches, A SHALL:
  - open the type menu;
  - go straight to the slots if the sentence names a bookable type;
  - reply with `REQUEST_ONLY_TEXT` if it names a request-only treatment (blanqueamiento,
    implantes, ortodoncia).

  A booking phrase SHALL NEVER book by itself (Decisions Q2).
- BK5. WHEN B returns an answer with `offer_booking: true`, A SHALL show it with a «Pedir cita»
  button (`bk:menu`).

### `offer_booking` in B (SPEC-001 R14; Decisions Q7)

- BK6. B's "Validar y componer" SHALL set `offer_booking: true` when the reply is `answered` and
  at least one cited fragment has `tipo` `tarifa` or `tratamiento`. In every other case it SHALL
  be `false`, and it SHALL never be `true` with an abstention, an error or an urgency. It SHALL be
  computed from the fragments, with no Gemini.
- BK7. B's "Resultado" SHALL add `offer_booking` to its whitelist. B SHALL still receive only
  `question` (SPEC-005 P5). **B SHALL be published before A.**

### Consent (Q8)

- BK8. Every booking step SHALL require consent in force. Without it, A SHALL reply with the
  SPEC-006 notice and discard the step (SPEC-006 C4).

### Type (Q3)

- BK9. The type menu SHALL offer the three bookable types, «Otro tratamiento» and «Hablar con
  recepción».
- BK10. WHEN «Otro tratamiento» is chosen, or `agenda_free_slots` returns `request_only`, A SHALL
  reply with `REQUEST_ONLY_TEXT`. Its «Primera visita» button SHALL lead to the slots for
  `primera_visita`. This is CONF-001 (a).

### Slots (Q4, Q5)

- BK11. WHEN a type is chosen, A SHALL call the public `agenda_free_slots(type, now, 3)`. It SHALL
  reply with `SLOTS_TEXT`, one button per slot (one per row, short Madrid label), «Ver más» and
  «Hablar con recepción». IF there are no slots, THEN it SHALL reply with `NO_SLOTS_TEXT`.
- BK12. WHEN «Ver más» is tapped, A SHALL show the next slots that start after the last one shown.
- BK13. Every booking callback SHALL fit in 64 bytes and carry its whole state (type and slot
  code). A SHALL store no booking state.
- BK14. A malformed `bk:` callback, or one with an unknown type, SHALL open the type menu. It
  SHALL never book.

### Confirmation and booking (US-004, RF-005, NFR-07; Q6, Q9)

- BK15. WHEN a slot is tapped, A SHALL reply with `CONFIRM_TEXT` and write nothing. «Elegir otro
  hueco» SHALL show the slots for that type again, from now.
- BK16. WHEN «Confirmar» is tapped, A SHALL call `agenda_book(type, start, from_id)` exactly
  once, and SHALL reply according to its result:
  - `booked` → `BOOKED_TEXT`;
  - `taken` → `TAKEN_TEXT` with the next slots;
  - `invalid` → `UNAVAILABLE_TEXT` with the next slots. For `request_only` or `unknown_type` it
    SHALL reply with the type menu instead;
  - `limit` → `LIMIT_TEXT` with the patient's existing appointment (BK18).

  The slot from the button SHALL never be trusted: `agenda_book` re-checks every rule (SPEC-004
  G10).
- BK17. Double booking SHALL stay impossible end to end: A adds no booking path besides
  `agenda_book`, whose exclusion constraints guarantee NFR-07 (SPEC-004 G12–G13). A repeated
  «Confirmar» SHALL get `limit`, not a second appointment.

### My appointment (Q10)

- BK18. WHEN `/micita` arrives with consent in force, A SHALL reply with `MY_APPOINTMENT_TEXT`
  for the patient's next `booked` future appointment, or with `NO_APPOINTMENT_TEXT`.
- BK19. A new SQL function `agenda_my_next(from_id)` SHALL return only the **type code** and the
  start and end of the subject's next `booked` appointment starting after now (the texts build
  «una limpieza» from the code; human, 2026-11-22). It SHALL return
  no professional, room, subject or id.
  - It SHALL follow SPEC-004's pattern: the public function takes no time parameter, and an
    internal `agenda_my_next_at(from_id, now)` serves the tests.
  - It SHALL live in `app/infra/sql/004_booking.sql`, which is idempotent and touches no other
    feature's data.

### Errors (Q12)

- BK19b. A SHALL make **two** Neon queries for booking (approved by the human at the R1 review,
  2026-11-22):
  - `agenda`: the patient's next appointment and, when a type is known, its free slots;
  - `book`: the booking, plus the next slots or the existing appointment when needed.
- BK20. IF any Neon call of a booking step fails, THEN A SHALL reply with the D7 text and
  «Hablar con recepción», and SHALL not retry. A failure at «Confirmar» SHALL be reported the
  same way: the patient can check with `/micita`.

### Privacy and logging (Q7, Q11)

- BK21. No booking step SHALL call B or Gemini. B SHALL never receive the `from.id`, a subject, a
  slot or any booking data.
- BK22. A SHALL keep its SPEC-005 settings: it saves no executions. This spec SHALL add no log or
  counter table. The only booking record is the appointment row (SPEC-004 G15). The PRD target
  "citas creadas por el bot" is computed from `agenda_appointments` with `channel = 'telegram'`.

### Code, tests and order of work (Q13)

- BK23. The texts, the callback codec, the phrase detector, the date formatting and the booking
  decisions SHALL live in `n8n/code/citas.js`.
  - The Code nodes that use it SHALL carry exactly that code, plus only their wiring.
  - A Node test, written before the module, SHALL cover:
    - every callback and the 64-byte limit;
    - command parsing (`/cita`, `/micita`, any letter case);
    - a phrase dataset with positives and **the negatives of BK3**: 0 negatives may match, and
      every positive must;
    - Madrid date formatting across both DST changes;
    - every text;
    - every decision of BK1–BK20.
  - A sync check SHALL compare the module with A's export.
- BK24. `agenda_my_next` SHALL be tested first with pytest on the Neon **test branch only**, and
  applied to `main` only after the human confirms, with a read-only before-and-after check
  (SPEC-004 G20).
- BK25. The changes to B and A SHALL be tested with pinned data under the SPEC-005 A4 extension
  (Decisions Q13):
  - fake ids `9000xx`;
  - one run per scenario;
  - `saveManualExecutions` disabled afterwards;
  - **every pinned datum removed and checked**;
  - the executions deleted by the human.
- BK26. The first task SHALL check the host behind each credential used (AGENTS.md "Preflight
  check").
- BK27. A and B SHALL be re-exported with no secret or personal data, following the SPEC-005
  procedure. The README SHALL describe the booking flow, `/cita`, `/micita` and the limitations.

## Acceptance criteria

**Node, SQL and pinned runs:**

- [ ] The `citas.js` test is green.
  - Every `bk:` callback is at most 64 bytes.
  - The commands are parsed in any case.
  - **Every positive booking phrase matches, and none of the negatives does**: «tengo una cita
    el lunes», «¿cuánto cuesta una cita?», «cancelar mi cita», «cambiar mi cita» and the others.
  - Labels and dates are correct in Madrid across both DST changes.
- [ ] `agenda_my_next` on the test branch:
  - it returns the next future `booked` appointment of the subject only, with no professional,
    room or subject;
  - it returns nothing when there is none, or when the only one is past or cancelled;
  - the public function has no time parameter.
- [ ] Pinned runs:
  - `taken` and `invalid` at «Confirmar» reply with the next slots;
  - `limit` replies with the existing appointment;
  - a Neon failure replies with D7;
  - a malformed `bk:` callback opens the menu.
- [ ] B: an answer citing TAR-001 or TRA-001 has `offer_booking: true`. An abstention, an error,
  an urgency or an answer citing only HOR-001 has `false`.

**From Telegram, with a test account that has consent** (B published before A):

- [ ] `/cita` → the type menu. «Limpieza» → up to 3 slots with short Madrid labels, «Ver más» and
  «Hablar con recepción».
- [ ] A slot → `CONFIRM_TEXT` with type, full date and time. «Confirmar» → `BOOKED_TEXT`, and
  `main` has one `booked` row for the account (read-only check, subject not printed).
- [ ] `/micita` → `MY_APPOINTMENT_TEXT` with that appointment. `/cita` again → `LIMIT_TEXT`. A
  second tap on the old «Confirmar» → `LIMIT_TEXT`.
- [ ] «¿Cuánto cuesta una limpieza?» → the usual 60 € answer with a «Pedir cita» button, which
  opens the type menu.
- [ ] «quiero pedir cita para una limpieza» → the slots directly. «Otro tratamiento» →
  `REQUEST_ONLY_TEXT`; its «Primera visita» → the slots for `primera_visita`.
- [ ] «tengo una cita el lunes», «¿cuánto cuesta una cita?» and «cancelar mi cita» → not the
  booking flow (they go to B as today). «me duele una muela, quiero cita» → the urgency reply.
- [ ] Without consent, `/cita`, `/micita` and a booking phrase → the consent notice.
- [ ] No B execution exists for any booking step, and no Gemini call is made for one. The B
  executions of the other messages contain only `question`.
- [ ] A and B are re-exported with no secret or personal data. A still saves no executions, and
  no pinned data remains in either workflow.

## Known limitations

- Reception cannot see who booked (SPEC-004; RF-007).
- There are no reminders and no self-service changes: the texts send the patient to reception.
- A's transient window (SPEC-005): n8n's local database holds the raw update for up to about 15
  minutes.
- The free-text detector is a strict phrase list, so unusual wordings get an ordinary answer.
  `/cita` and «Pedir cita» always work.
- A failure at «Confirmar» cannot tell whether the booking was saved. `/micita` resolves it.
- All agenda data is example data (DEP-01, DEP-03). The appointment type is health data
  (DEP-04).

## Out of scope

- Moving and cancelling (US-005), including what happens to appointments when consent is
  withdrawn (proposed SPEC-008).
- Reminders and the chat id table (US-006, RF-006, CONF-005; proposed SPEC-009).
- The reception panel and patient identification (RF-007).
- Choosing a professional, dates or times typed as text, recurring appointments, and booking for
  someone else.
- Any change to the agenda rules or to the SPEC-004 functions, beyond adding `agenda_my_next`.
