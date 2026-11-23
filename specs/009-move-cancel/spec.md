---
type: spec
spec_id: SPEC-008
title: move and cancel — Functional Spec
description: Requirements for moving and cancelling one's own appointment from Telegram on the SPEC-004 agenda (US-005, RF-005) — the «Mi cita» view with «Cambiar» and «Anular», strict free-text phrases, a confirmation before every write, a configurable minimum notice, a move done in one transaction that keeps the old appointment if the new slot fails, cancelled rows kept until the normal purge, safe old buttons, and the appointment kept (with a cancel button) when consent is withdrawn. All in flow A and Neon, never through B or Gemini. EARS notation.
tags: [spec, move, cancel, SPEC-008, US-005, RF-005, NFR-07, SPEC-004, SPEC-006, SPEC-007]
status: implemented
sources: [./clarifications.md, ../../docs/03-prd.md, ../007-agenda/spec.md, ../008-booking/spec.md, ../006-consent/spec.md, ../005-pseudonymized-log/spec.md, ../004-urgencies/spec.md, ../constitution.md]
generated: { by: claude-code, at: 2026-11-23T00:00:00Z }
verified: { by: human, at: 2026-11-23T00:00:00Z }
stale_after: null
---

# move and cancel — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-005), §5.1 (RF-005, move and cancel), §5.2 (NFR-07),
§8 (R-05), §9 (DEP-03, DEP-04), §10 (CONF-004); charter §4. It builds on SPEC-004
(`specs/007-agenda/`, and its Q9), SPEC-007 (`specs/008-booking/`), SPEC-006
(`specs/006-consent/`), SPEC-005 (`specs/005-pseudonymized-log/`) and SPEC-003
(`specs/004-urgencies/`). Decisions in [clarifications](./clarifications.md).

## Context

Hoy el bot da citas, pero para cambiarlas o anularlas hay que llamar a recepción. Esta spec deja
hacerlo desde Telegram:

- el paciente ve su cita con los botones «Cambiar» y «Anular», bajo `/micita` y bajo los mensajes
  que ya la muestran, o escribiendo una frase clara como «cancelar mi cita»;
- antes de anular o de mover, el bot repite la cita y pide confirmación;
- al mover, la cita antigua solo se anula si la nueva queda reservada;
- con menos de 2 horas de antelación, el bot manda a recepción;
- si el paciente retira el consentimiento, su cita se mantiene y puede anularla igualmente.

Todo ocurre en el flujo A y en Neon: B y Gemini no intervienen. Los recordatorios y el panel de
recepción vienen después.

**Definitions.**

- *Current appointment*: the subject's `booked` appointment that starts after now. There is at
  most one (SPEC-004 limit, clarifications A3).
- *«Mi cita» view*: the current appointment with the buttons «Cambiar» · «Anular» · «Hablar con
  recepción», or `NO_APPOINTMENT_TEXT` with «Pedir cita» when there is none.
- *Change step*: any update handled by this spec: a change or cancel button (`bk:v`, `bk:a`,
  `bk:ac`, `bk:x`, `bk:xm`, `bk:xs`, `bk:xc`), or a change or cancel phrase.
- *Change or cancel phrase*: a pseudonymized text that matches the fixed, strict list of the
  booking module for changing or cancelling an appointment (clarifications Q2).
- *Start code*: the start of an appointment or a slot as minutes since the Unix epoch, in base
  36, as in SPEC-007.
- *Change callbacks*, each at most 64 bytes. They are in the `bk:` namespace of SPEC-007, and
  they carry no type: the functions read it from the appointment.

  | `callback_data` | Meaning |
  |---|---|
  | `bk:v` | the «Mi cita» view («Mantener mi cita» while moving) |
  | `bk:v:<start>` | «Mantener mi cita» in the cancel confirmation (also without consent, MC10) |
  | `bk:a:<start>` | «Anular» → the cancel confirmation |
  | `bk:ac:<start>` | «Sí, anular» |
  | `bk:x:<start>` | «Cambiar» → the slots for the move |
  | `bk:xm:<start>:<from>` | «Ver más» while moving, after the slot `<from>` |
  | `bk:xs:<start>:<new>` | a slot while moving → the move confirmation |
  | `bk:xc:<start>:<new>` | «Confirmar cambio» |

  `<start>` is always the start of the appointment the button refers to (clarifications Q7).
- *Minimum notice* (`change_min_lead`): how long before the start of the current appointment the
  bot can still cancel or move it. Example value **2 hours** (clarifications Q4).
- *Booking module*: `n8n/code/citas.js` (SPEC-007), extended by this spec.

**Fixed texts.** The texts of clarifications Q11, approved by the human on 2026-11-23. `{tipo}`
is the type with its article («una limpieza»), and dates are Madrid dates as in SPEC-007.

- **Changed SPEC-007 texts.** Each one drops «llama a recepción», because the buttons replace
  it, and gets «Cambiar» · «Anular» · «Hablar con recepción»:
  - `BOOKED_TEXT`: «Hecho: tienes {tipo} el {fecha} a las {hora}.»
  - `LIMIT_TEXT`: «Ya tienes {tipo} el {fecha} a las {hora}. Solo se puede tener una cita
    reservada por el bot.»
  - `MY_APPOINTMENT_TEXT`: «Tu próxima cita: {tipo} el {fecha} a las {hora}.»
- **New texts:**
  - `CANCEL_CONFIRM_TEXT`: «¿Seguro que quieres anular {tipo} del {fecha} a las {hora}?»
    Buttons «Sí, anular» (`bk:ac:<start>`) · «Mantener mi cita» (`bk:v:<start>`).
  - `CANCELLED_TEXT`: «Hecho: he anulado {tipo} del {fecha} a las {hora}. Si quieres otra,
    escribe /cita.» Button «Pedir cita».
  - `MOVE_SLOTS_TEXT`: «¿A cuándo quieres cambiar {tipo} del {fecha} a las {hora}? Estos son los
    primeros huecos:» The slot buttons, «Ver más», «Mantener mi cita» and «Hablar con
    recepción».
  - `MOVE_MORE_SLOTS_TEXT`: «Estos son los siguientes huecos:» The same buttons.
  - `MOVE_CONFIRM_TEXT`: «Vas a cambiar {tipo} del {fecha} a las {hora} al {fecha nueva} a las
    {hora nueva}. ¿Lo confirmo?» Buttons «Confirmar cambio» · «Elegir otro hueco» · «Mantener mi
    cita».
  - `MOVED_TEXT`: «Hecho: tu cita pasa al {fecha nueva} a las {hora nueva}. La anterior queda
    anulada.» Buttons «Cambiar» · «Anular» · «Hablar con recepción». **Changed by the human at the
    M1 review (2026-11-23).** The first wording, «Hecho: {tipo} pasa al…», read «Hecho: una
    limpieza pasa al…».
  - `MOVE_TAKEN_TEXT`: «Ese hueco se acaba de ocupar. Tu cita del {fecha} a las {hora} sigue
    igual. Estos son los siguientes:» The slot buttons.
  - `MOVE_UNAVAILABLE_TEXT`: «Ese hueco ya no está disponible. Tu cita del {fecha} a las {hora}
    sigue igual. Estos son los siguientes:» The slot buttons.
  - `MOVE_NO_SLOTS_TEXT`: «Ahora mismo no hay otros huecos para {tipo} en los próximos 30 días.
    Tu cita sigue igual. Llama a recepción para buscar otra fecha.» Button «Hablar con
    recepción».
  - `TOO_LATE_TEXT`: «Tu cita es en menos de {plazo}. Para cambiarla o anularla, llama a
    recepción.» Button «Hablar con recepción». `{plazo}` comes from `change_min_lead` («2 horas»).
  - `NOT_ACTIVE_TEXT`: «Esa cita ya no está activa.», followed by the «Mi cita» view.
  - `KEPT_TEXT`: «De acuerdo, mantengo tu cita.», followed by the «Mi cita» view.
  - `REVOKED_WITH_APPOINTMENT_TEXT`: the SPEC-006 `REVOKED_TEXT`, followed by «Sigues teniendo
    {tipo} el {fecha} a las {hora}. Si no vas a ir, puedes anularla aquí o llamar a recepción.»
    Button «Anular mi cita» (`bk:a:<start>`). **Changed by the human at the M1 review
    (2026-11-23).** The first wording, «Tu cita de {tipo} el…», read «Tu cita de una limpieza
    el…».
  - `REVOKED_LOOKUP_FAILED_TEXT` (human, spec review, 2026-11-23): the SPEC-006 `REVOKED_TEXT`,
    followed by «Si tenías una cita reservada, se mantiene; para anularla, llama a recepción.»
    No button.
  - On a Neon failure, the CHG-001 D7 text with «Hablar con recepción», as in SPEC-007.
- **Without consent** (MC10), the steps that are allowed show only what concerns that
  appointment (proposed by the agent, approved by the human at the spec review, 2026-11-23):
  - `CANCELLED_TEXT` without the «Si quieres otra, escribe /cita.» sentence and without «Pedir
    cita»;
  - `NOT_ACTIVE_TEXT` and `KEPT_TEXT` without the «Mi cita» view;
  - `TOO_LATE_TEXT` as it is.

## Requirements (EARS)

### Ways in and order (clarifications Q2)

- MC1. WHEN `/micita`, `LIMIT_TEXT` or `BOOKED_TEXT` shows the current appointment, A SHALL add
  the buttons «Cambiar» (`bk:x:<start>`), «Anular» (`bk:a:<start>`) and «Hablar con
  recepción».
- MC2. No new command SHALL be added. `/micita` is the way in (clarifications Q2).
- MC3. WHEN a text message arrives, A SHALL check, in this order:
  1. the urgency (SPEC-003);
  2. consent (SPEC-006);
  3. whether it is a change or cancel phrase;
  4. whether it is a booking phrase (SPEC-007);
  5. only then send it to B.

  An urgency SHALL always win: «quiero anular la cita, me sangra mucho la encía» gets the urgency
  reply. With consent in force, the phrase checks SHALL be skipped when «Detectar urgencia» found
  `urgent` or `severe`, as in SPEC-007 BK2.
- MC4. The change and cancel phrase list SHALL be fixed and strict.
  - Clear requests SHALL match, such as «cancelar mi cita», «quiero anular la cita», «cambiar mi
    cita», «necesito mover mi cita al jueves» and «no puedo ir a mi cita».
  - Statements, policy and price questions, and other people's appointments SHALL NOT match, and
    SHALL keep going to B: «me cambiaron la cita», «¿se puede cancelar sin coste?», «¿cuánto
    cuesta cancelar?», «la cita de mi madre» and «¿a qué hora es mi cita?».
  - These phrases SHALL stay negatives of the SPEC-007 booking detector, whose dataset does not
    change.
- MC5. WHEN a change or cancel phrase matches, A SHALL show the «Mi cita» view. A phrase SHALL
  NEVER cancel or move by itself, and no date or time SHALL be read from it.

### Cancel (US-005, RF-005; Q3, Q6)

- MC6. WHEN «Anular» is tapped, A SHALL reply with `CANCEL_CONFIRM_TEXT` for the appointment at
  the button's start, and SHALL write nothing.
- MC7. WHEN «Sí, anular» is tapped, A SHALL call `agenda_cancel(from_id, start)` exactly once, and
  SHALL reply according to its result:
  - `cancelled` → `CANCELLED_TEXT`;
  - `too_late` → `TOO_LATE_TEXT`;
  - `not_found` → `NOT_ACTIVE_TEXT` (MC17).
- MC8. A cancelled appointment SHALL keep its row with `status = 'cancelled'` and `cancelled_at`
  set. Its slot SHALL be offered again by `agenda_free_slots` at once. The row SHALL be deleted by
  the existing purge, 30 days after its original end (SPEC-004 G17).
- MC9. After a cancellation, `/micita` SHALL show `NO_APPOINTMENT_TEXT`, and `/cita` SHALL work
  again, because the limit counts only `booked` appointments.

### Consent (Q8)

- MC10. Every change step SHALL require consent in force, **except** «Anular» (`bk:a:<start>`),
  «Sí, anular» (`bk:ac:<start>`), and the «Mantener mi cita» of the cancel confirmation
  (`bk:v:<start>`; human, spec review, 2026-11-23). Those three SHALL work without consent, show
  only what concerns that appointment (see Fixed texts, "Without consent"), and never open any
  other step. Without consent, any other change step, including `bk:v` without a start, SHALL
  get the SPEC-006 notice and be discarded (SPEC-006 C4).
- MC11. WHEN the patient withdraws consent AND has a current appointment, A SHALL keep the
  appointment `booked`, and SHALL reply with `REVOKED_WITH_APPOINTMENT_TEXT` instead of
  `REVOKED_TEXT`. Without a current appointment, the reply SHALL stay `REVOKED_TEXT`.
  Withdrawing SHALL never delete or cancel an appointment.
- MC12. The withdrawal itself SHALL NOT depend on the agenda: the appointment lookup SHALL run
  only after the withdrawal is saved. IF that lookup fails, THEN the withdrawal SHALL stand, and
  A SHALL reply with `REVOKED_LOOKUP_FAILED_TEXT` (human, spec review, 2026-11-23).

### Move (RF-005, NFR-07; Q3, Q5)

- MC13. WHEN «Cambiar» is tapped, A SHALL call `agenda_free_slots(type, now, 3)` for the type of
  the appointment, and SHALL reply with `MOVE_SLOTS_TEXT`.
  - The current appointment's start SHALL NOT be offered.
  - «Ver más» SHALL show the next slots after the last one shown, with `MOVE_MORE_SLOTS_TEXT`.
  - IF there are no other slots, THEN A SHALL reply with `MOVE_NO_SLOTS_TEXT`.
- MC14. WHEN a slot is tapped while moving, A SHALL reply with `MOVE_CONFIRM_TEXT`, and SHALL
  write nothing. «Elegir otro hueco» SHALL show the move slots again, from now.
- MC15. WHEN «Confirmar cambio» is tapped, A SHALL call `agenda_move(from_id, old_start,
  new_start)` exactly once, and SHALL reply according to its result:
  - `moved` → `MOVED_TEXT`;
  - `taken` → `MOVE_TAKEN_TEXT` with the next slots;
  - `invalid` → `MOVE_UNAVAILABLE_TEXT` with the next slots;
  - `too_late` → `TOO_LATE_TEXT`;
  - `not_found` → `NOT_ACTIVE_TEXT`.
- MC16. `agenda_move` SHALL be **all or nothing**. On `moved`:
  - the old appointment is `cancelled`, with `cancelled_at` set and `replaced_by` pointing to the
    new one;
  - the new appointment is `booked`, with the same type and subject.

  On every other result, **the old appointment SHALL stay `booked` and unchanged**, and nothing
  new SHALL be created.
  - The move SHALL keep the same type. It SHALL NOT be refused because of the limit of 1, since
    the subject keeps exactly one future appointment.
  - A new start that overlaps the old appointment, with the same professional or room, SHALL be
    allowed.
  - NFR-07 SHALL still hold. The new appointment is checked by the same exclusion constraints,
    so two patients moving into the same slot give one `moved` and one `taken`.

### Old buttons and the minimum notice (Q4, Q7)

- MC17. Every cancel and move function SHALL act only on the subject's `booked` appointment that
  starts **at the button's start** and after now. IF there is none (the appointment is past,
  cancelled or already moved, or the start belongs to someone else), THEN it SHALL change
  nothing and SHALL return `not_found`. A SHALL reply with `NOT_ACTIVE_TEXT` followed by the «Mi
  cita» view. A second tap on «Sí, anular» or «Confirmar cambio» SHALL therefore change nothing.
- MC18. IF the appointment starts less than `change_min_lead` after now, THEN cancelling and
  moving SHALL change nothing and SHALL return `too_late`. The confirmations (MC6, MC14) SHALL
  check this before they are shown, so the patient gets `TOO_LATE_TEXT` straight away.
- MC19. `change_min_lead` SHALL be a setting in `agenda_settings`, **2 hours**, marked as example
  data. The clinic confirms the real policy under DEP-03.
- MC20. The new slot of a move SHALL follow the SPEC-004 booking rules, checked by
  `agenda_slot_problem` for the appointment's type. A new start equal to the old one SHALL give
  `invalid` with `same_slot`.

### SQL (Q6, Q9)

- MC21. A new file, `app/infra/sql/005_move_cancel.sql`, SHALL add:
  - `agenda_cancel_at(from_id, start, now)` and the public `agenda_cancel(from_id, start)`,
    returning `result` (`cancelled`, `not_found`, `too_late`), `type_code`, `starts_at` and
    `ends_at`;
  - `agenda_move_at(from_id, old_start, new_start, now)` and the public `agenda_move(from_id,
    old_start, new_start)`, returning `result` (`moved`, `taken`, `invalid`, `not_found`,
    `too_late`), `reason` for `invalid`, `type_code`, and the old and the new start and end;
  - the columns `cancelled_at timestamptz` and `replaced_by uuid` on `agenda_appointments`, and
    `change_min_lead interval` on `agenda_settings`, all added only if missing.
- MC22. The public functions SHALL take no time parameter and SHALL use `now()`. Every function
  SHALL purge first, take the subject's advisory lock (the same one as `agenda_book`), compute the
  subject from `from_id` in Postgres, and return no professional, room, subject or id.
- MC23. The file SHALL be idempotent, and SHALL change neither the data of `kb_fragments`,
  `consent` and `consent_key`, nor the existing agenda rows. Existing appointments SHALL keep
  `cancelled_at` and `replaced_by` empty.

### Errors (Q11)

- MC24. IF any Neon call of a change step fails, THEN A SHALL reply with the D7 text and «Hablar
  con recepción», and SHALL not retry. A failure at «Sí, anular» or «Confirmar cambio» SHALL be
  reported the same way: the patient can check with `/micita`.

### Privacy and logging (Q12)

- MC25. No change step SHALL call B or Gemini. B SHALL never receive the `from.id`, a subject, a
  start or any appointment data. B SHALL NOT change in this spec.
- MC26. A SHALL keep its SPEC-005 settings and save no executions. No log or counter table SHALL
  be added. The only records are the appointment rows.

### Code, tests and order of work (Q10, Q13)

- MC27. The texts, the change callbacks, the phrase detector and the change decisions SHALL live
  in `n8n/code/citas.js`. The Code nodes that use it SHALL carry exactly that code plus their
  wiring, checked by the sync test against A's export.
- MC28. A Node test, written before the code, SHALL cover:
  - every change callback and the 64-byte limit;
  - a change and cancel phrase dataset, with the positives and the negatives of MC4: every
    positive must match, and 0 negatives may. The SPEC-007 booking dataset must stay as it is,
    with every one of its results unchanged;
  - the order of MC3 with mixed messages (urgency, change, booking);
  - every text and every decision of MC1–MC20, with and without consent;
  - that every keyboard has **1 to 6 rows** of one button.
- MC29. A SHALL send keyboards of up to 6 rows. It SHALL keep the SPEC-007 pattern: one Telegram
  node per number of buttons, with fixed rows and one expression per button field. So it gains
  «Responder reserva (6)» and a sixth rule in «¿Cuántos botones?». The whole keyboard SHALL never
  be one expression (SPEC-007 R6).
- MC30. The SQL SHALL be tested first with pytest on the Neon **test branch only**, with fake ids
  `9008xx`. It SHALL be applied to `main` only after the human confirms, with a read-only check
  before and after (SPEC-004 G20).
- MC31. The changes to A SHALL be tested with pinned data under the SPEC-005 A4 extension
  approved on 2026-11-23:
  - fake ids `9008xx`;
  - one run per scenario;
  - `saveManualExecutions` disabled afterwards;
  - **every pinned datum removed and checked**;
  - the executions deleted by the human.
- MC32. The first task SHALL check the host behind each credential used (AGENTS.md "Preflight
  check").
- MC33. A SHALL be re-exported from its published version, without the `shared` and `pinData`
  blocks, and with no secret or personal data. The README SHALL describe changing and
  cancelling, the minimum notice, what happens on withdrawal, and the limitations.

## Acceptance criteria

All met on 2026-11-23 (M0–M6). Each criterion says how it was checked. Where the Telegram test
did not repeat a case, the M4 pinned run that covers it is named (execution numbers, deleted
afterwards by the human).

**Node, SQL and pinned runs:**

- [x] The `citas.js` test is green (M1).
  - Every change callback is at most 64 bytes. The longest is 17.
  - **Every positive change or cancel phrase matches, and no negative does:** 23/23 and 0/22.
    The SPEC-007 booking dataset gives the same results as before, 25/25 and 0/25, and the two
    detectors never overlap.
  - «quiero anular la cita, me sangra mucho la encía» → urgency. «quiero cambiar la cita que
    pedí» → the «Mi cita» view, not the booking menu.
  - Every keyboard has 1–6 rows of one button.
- [x] On the test branch (M2; `tests/infra/test_move_cancel_sql.py`, 36 tests):
  - `agenda_cancel` sets the row to `cancelled` with `cancelled_at`, and the slot is offered
    again;
  - it gives `not_found` for another subject's appointment, a past one, a cancelled one and a
    wrong start, and `too_late` inside `change_min_lead`, changing nothing;
  - `agenda_move` gives `moved`, with the old row `cancelled` and `replaced_by` set, and the new
    row `booked`;
  - `taken`, `invalid`, `same_slot`, `too_late` and `not_found` leave the old row `booked` and
    unchanged, and create nothing;
  - a move 15 minutes later, with the same professional, succeeds;
  - **concurrency:**
    - two patients moving into the same free slot → 1 `moved` and 1 `taken`, and the loser keeps
      their appointment;
    - a move and an `agenda_book` of the same subject at the same time → 1 `moved` and 1
      `limit`;
    - a double «Sí, anular» → 1 `cancelled` and 1 `not_found`;
  - the public functions have no time parameter;
  - re-applying the schema changes neither `kb_fragments`, `consent`, the key, nor the agenda
    rows. On `main` (M3), the before-and-after check confirmed the same.
- [x] Pinned runs (M4, 39 scenarios):
  - every result of cancel and move gives its text;
  - an old button gives `NOT_ACTIVE_TEXT`;
  - a Neon failure gives D7;
  - without consent, only «Anular», «Sí, anular» and the «Mantener mi cita» of the cancel
    confirmation work. `bk:v` without a start, «Cambiar» and a change phrase get the notice;
  - the withdrawal with an appointment gives `REVOKED_WITH_APPOINTMENT_TEXT` with «Anular mi
    cita», and without one `REVOKED_TEXT`;
  - **a failed appointment lookup at withdrawal** (pinned error) leaves the consent `revoked`, and
    gives `REVOKED_LOOKUP_FAILED_TEXT`: `REVOKED_TEXT` followed by «Si tenías una cita reservada, se
    mantiene; para anularla, llama a recepción.», with no button.
  - A failure in «Guardar retirada» itself cannot be pinned: pinned data always leaves through
    the normal output. Its error path did not change (→ «Tras guardar» → D7), and the export
    shows it.

**From Telegram, with a test account that has consent and a current appointment** (the
appointment kept for the demo was on 23/11/2026 at 9:00, so the test booked a new one first;
human, M5, 2026-11-23):

- [x] `/micita` → `MY_APPOINTMENT_TEXT` with «Cambiar», «Anular» and «Hablar con recepción».
- [x] «Cambiar» → the slots, without the current one, and «Ver más». A slot → `MOVE_CONFIRM_TEXT`
  with both dates. «Confirmar cambio» → `MOVED_TEXT`. `main` has the old row `cancelled` with
  `replaced_by` pointing to the new `booked` row (read-only check, no subject printed). A second
  «Confirmar cambio» → `NOT_ACTIVE_TEXT` and the new appointment.
- [x] «Anular» → `CANCEL_CONFIRM_TEXT`. «Mantener mi cita» → `KEPT_TEXT`. «Anular» → «Sí, anular» →
  `CANCELLED_TEXT` with «Pedir cita». «cancelar mi cita» without an appointment → the view with
  `NO_APPOINTMENT_TEXT`. An old «Anular» → `NOT_ACTIVE_TEXT` is covered by the M4 pinned runs
  (214, 217).
- [x] After booking again: «Retirar consentimiento» → `REVOKED_WITH_APPOINTMENT_TEXT` («Sigues
  teniendo una limpieza el miércoles 25…»). «Anular mi cita» → «Sí, anular» works without consent,
  and cancels with only «Hablar con recepción». `/micita` without consent → the notice is covered
  by SPEC-007's pinned run 27 and by `consentimiento.test.js`. The human then accepted again.
- [x] An urgency with a cancel phrase → the urgency reply (B, 261). «me cambiaron la cita» → B is
  covered by the M4 pinned run 209 (`model_abstained`). «¿se puede cancelar sin coste?» is a
  negative of the phrase test.
- [x] No B execution exists for any change step. B's executions since publishing (245, 261 and
  263) contain only `question`.
- [x] A is re-exported from its published version (`7c3d4100…`), without `shared` and `pinData`,
  with no secret or personal data (M6). A still saves no executions (none / none / false / false),
  and no pinned data remains. B did not change: its export equals the one in git.

## Known limitations

- **Reception is not told** about cancellations or moves until RF-007. It sees them only in its
  read-only SQL view.
- **The minimum notice is an example value** (2 hours) until the clinic states its policy
  (DEP-03).
- **The appointment after a withdrawal** is kept with no legal basis decided yet (DEP-04).
- A's transient window (SPEC-005) applies to these messages too.
- The free-text detector is a strict phrase list. Unusual wordings go to B, and `/micita` always
  works.
- A failure at «Sí, anular» or «Confirmar cambio» cannot tell whether it was saved. `/micita`
  resolves it.
- A keyboard has at most 6 rows (MC29).

## Out of scope

- Reminders, with their confirm and cancel buttons and the chat id table (US-006, RF-006,
  CONF-005; proposed SPEC-009). They will reuse `agenda_cancel`.
- The reception panel, its notifications and patient identification (RF-007).
- Changing the type of an appointment (a cancel plus `/cita`), choosing a professional, dates
  typed as text, and more than one future appointment per patient.
- Appointments made by reception or by phone: the agenda only has the bot's.
- Asking or storing a reason for cancelling.
- Any change to B, to the consent tables, or to the SPEC-004 and SPEC-007 functions.
