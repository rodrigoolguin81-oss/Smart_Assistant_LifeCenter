---
type: plan
spec_id: SPEC-007
title: booking — Technical Plan
description: How to build booking from Telegram — preflight (credential hosts), citas.js and the consent module extension test-first, agenda_my_next in 004_booking.sql, offer_booking in B, the booking branch of A with a dynamic inline keyboard, pinned runs, the Telegram test (B before A), and exports and docs.
tags: [plan, booking, SPEC-007, n8n, neon]
status: implemented
sources: [./spec.md, ./clarifications.md, ../007-agenda/plan.md, ../006-consent/plan.md, ../005-pseudonymized-log/plan.md]
generated: { by: claude-code, at: 2026-11-22T00:00:00Z }
verified: { by: human, at: 2026-11-22T00:00:00Z }
stale_after: null
---

# booking — Plan

Same order as SPEC-003, SPEC-006 and SPEC-004:

1. A read-only preflight.
2. The JavaScript modules, test-first.
3. The SQL function, test-first: on the test branch, then `main`, **each after the human
   confirms**.
4. B, then A, with pinned data under the A4 extension.
5. The human publishes **B, then A**, and tests from Telegram.
6. Exports and docs.

## Architecture

```text
A  lifecenter-telegram-demo (saves NO executions)
   Telegram Trigger → Clasificar (consentimiento.js: + kinds booking_command, booking_button)
     → ¿Qué ha llegado?
         ├─ Recepción → (D8, unchanged)
         ├─ Consentimiento / booking buttons (bk:…) → Confirmar botón de consentimiento ─┐
         ├─ Comando (/start, /privacidad, /cita, /micita) ───────────────────────────────┤
         ├─ Otro ────────────────────────────────────────────────────────────────────────┤
         └─ Texto → Seudonimizar → Detectar urgencia ────────────────────────────────────┤
                                                                                         ▼
        Consultar consentimiento → Decidir (consentimiento.js: + action 'booking')
          → ¿Qué hacer?
              ├─ core     → ¿Es una reserva? (citas.js, phrase detector)
              │               ├─ sí → Preparar reserva ─┐
              │               └─ no → Llamar al núcleo ──question──▶ B → Componer respuesta
              │                                                (+ «Pedir cita» if offer_booking)
              ├─ booking  → Preparar reserva (citas.js: which step, which query)
              │               → ¿Qué consulta?
              │                   ├─ none    ─────────────────────────────────┐
              │                   ├─ my_next → Mi próxima cita   (Neon) ──────┤ (each with an
              │                   ├─ slots   → Buscar huecos     (Neon) ──────┤  error output
              │                   └─ book    → Reservar          (Neon) ──────┤  → D7)
              │                                                                ▼
              │                            Componer reserva (citas.js: text + keyboard rows)
              ├─ accept / withdraw / reply  (unchanged)
          → ¿Qué teclado? (+ 'offer' → Responder con pedir cita;
                           + 'booking' → ¿Cuántos botones? → Responder reserva (1)…(5))
            (R6: one Telegram node per number of buttons, each with fixed rows and one
             expression per button field; the whole-keyboard expression was dropped by n8n)

B  lifecenter-demo-core: "Validar y componer" + offer_booking; "Resultado" whitelist + offer_booking.
Neon: 004_booking.sql → agenda_my_next(from_id) / agenda_my_next_at(from_id, now)
```

B is never on the booking path. Every booking query goes from A straight to Neon with `from.id`
as a parameter (BK21).

## Step 0: Preflight, read-only (BK26, AGENTS.md)

**The agent, with read-only access only:**

- **`.env` hosts:** print the hosts of `DIRECT_URL` and `TEST_DATABASE_URL`. They must differ and
  be two branches (`neon.branch_id`) of the same project.
- **SPEC-004 on both branches:** the 7 `agenda_*` functions exist, and on `main` the
  configuration is still 3 / 3 / 5 / 11 / 1 with 0 appointments. `agenda_my_next` does not exist
  yet.
- **The `Neon main` credential in n8n:** the MCP and the API cannot read a credential's fields,
  so its host cannot be read by the agent.
  - The agent records what the MCP shows (`list_credentials`: name, type, id and, if listed, the
    last update), to see whether it changed after the SPEC-006 K5 fix.
  - The **evidence on record** is that SPEC-006 K5's acceptance, written by A through `Neon
    main`, was read back from `main` (22/11/2026 17:04), and `main` still has that row.
- **The human, from the n8n UI** (nothing is saved):
  1. Open **Overview → Credentials → «Neon main»**.
  2. Check that **Host** is `ep-steep-resonance-…`, the
     host of `DIRECT_URL`, not the `ep-blue-firefly-…` of the test branch. Check also that
     **Database** is `neondb` and **User** is `neondb_owner`.
  3. Check that **SSL** is `require`, and that **CA Certificate, Client Private Key and Client
     Certificate are empty**. The browser autofilled them in SPEC-006.
  4. Close it **without saving** (no "Save", no "Test" needed), and tell the agent what was
     seen.
- **n8n:**
  - check in the Telegram node's code that its inline keyboard is read with `getNodeParameter`
    and built from `rows[].row.buttons[]`, so a single expression can return the whole
    keyboard. This is already seen in n8n 2.48.4, `GenericFunctions.js`. **R6 showed this is not
    enough:** the parameter is normalized before that code reads it (see Step 5);
  - check that the B and A exports in git are the published versions.

## Step 1: The JavaScript modules, test-first (BK23)

**`n8n/code/citas.js`**, paste-ready like the others:

- **Texts and labels:** every fixed text of the spec, the type names (from the agenda codes),
  and the button labels.
- **Codec:**
  - `encodeSlot(date)` gives minutes since the epoch in base 36; `decodeSlot(code)` is the
    reverse;
  - `bk(kind, type, slot)` builds each callback;
  - `parseBookingCallback(data)` returns `{ step: 'menu' | 'type' | 'other' | 'slot' |
    'confirm' | 'more' | 'retry' | 'malformed', type, start }`. An unknown type gives
    `malformed`.
- **`detectBookingPhrase(text)`** returns `{ match, type | null, requestOnly }`.
  - It uses a strict list of request patterns (pedir / reservar / coger / dar cita, quiero una
    cita, ¿me das cita?, …).
  - It **blocks** patterns for an existing appointment, prices, moving and cancelling (tengo /
    mi cita, cuánto cuesta, cancelar / anular / cambiar / mover).
  - It detects a bookable type named in the sentence, and request-only words.
  - It works on the normalized, pseudonymized text, like `urgencias.js`.
- **Formatting:** `shortLabel(date)` gives «lun 7 dic · 9:00» and `longDate(date)` gives «lunes 7
  de diciembre», plus the year when needed, both in Europe/Madrid. `hour(date)` gives «9:00».
- **`prepare(route, phrase, now)`** decides the step and the query: `none`, `my_next` (for
  `/cita` and `/micita`), `slots` (type, from) or `book` (type, start).
- **`compose(step, dbResult)`** returns `{ text, keyboard: [[{ text, data }], …] }` for every
  result of BK9–BK20, including the D7 error.

**`n8n/code/consentimiento.js` (the SPEC-006 module), extended test-first:**

- `parseCommand` also recognizes `cita` and `micita`, in any letter case.
- `parseCallback` classifies any `bk:…` as `booking_button`, keeping the raw data.
- `decide`:
  - with consent in force, `booking_command` and `booking_button` → action `booking`;
  - without consent → the notice;
  - lookup failed → D7;
  - `text` stays `core` (the phrase check comes after, in A).
- The existing tests stay green, and new rows are added to the decision table.

**Tests:**

- **`n8n/code/citas.test.js`:**
  - every callback ≤ 64 bytes, and the round trip of the codec, including dates in 2084;
  - the **phrase dataset** `evals/booking_phrases.yaml`: about 25 positives and about 25
    negatives, including «tengo una cita el lunes», «¿cuánto cuesta una cita?», «cancelar mi
    cita», «cambiar mi cita», «¿a qué hora es mi cita?» and «la cita de mi madre». Every
    positive must match and **0** negatives may;
  - the labels across both DST changes;
  - every text;
  - every `prepare` and `compose` case;
  - a sync check with A's nodes «¿Es una reserva?», «Preparar reserva» and «Componer reserva».
- **`n8n/code/consentimiento.test.js`:** the new kinds and decisions.

## Step 2: `004_booking.sql` on the test branch [asks for confirmation first] (BK19, BK24)

- `agenda_my_next_at(p_from_id text, p_now timestamptz)` returns `(type_name text, starts_at
  timestamptz, ends_at timestamptz)`.
  - It returns the subject's (`agenda_subject`) earliest `booked` appointment with `starts_at >
    p_now`, joined to `agenda_types` for the name.
  - It returns no other column.
  - It purges first, like the other agenda functions.
- `agenda_my_next(p_from_id text)` is the public version, which uses `now()` and has no time
  parameter.
- **Test first:** `tests/infra/test_booking_sql.py`, on the test branch only, with fake ids. It
  covers:
  - none, one and several future appointments (it returns the earliest);
  - past and cancelled appointments are ignored;
  - another subject's appointment is invisible;
  - the exact column list, and no `p_now` in the public signature;
  - every session time zone;
  - re-applying the schema leaves `kb_fragments`, `consent`, the key and the agenda unchanged.
- The run order is the same as SPEC-004 E2: red (with nothing created), the schema, green, then
  all of `tests/infra`.

## Step 3: `main` [asks for confirmation first] (BK24)

The same read-only before-and-after check as SPEC-004 E3:

- `kb_fragments` rows and md5;
- `consent` and `consent_key` unchanged (digests compared inside the script);
- the agenda configuration and appointment count unchanged;
- 2 new functions.

## Step 4: B (`lifecenter-demo-core`) through the MCP, with pinned data (BK6, BK7)

- **"Validar y componer":** after a validated answer, `offer_booking = result.cited.some((f) =>
  ['tarifa', 'tratamiento'].includes(f.tipo))`. Every other return sets `offer_booking: false`.
- **"Resultado":** `offer_booking` is added to `KEEP`.
- **Pinned runs** (B's trigger pinned with `{ question }`, Postgres and Gemini pinned), one per
  case:
  - a TAR-001 answer → `true`;
  - a TRA-001 answer → `true`;
  - an HOR-001-only answer → `false`;
  - `below_threshold` → `false`;
  - `model_abstained` → `false`;
  - an urgency → `false`.
- B saves its executions as always; they are deleted by the human with the others.

## Step 5: A through the MCP, with pinned data (BK1–BK22)

**Nodes:**

- **new:**
  - «¿Es una reserva?» (Code, citas.js). It calls `bookingPhraseFor(question, urgency)` with
    «Detectar urgencia»'s output, so an urgency always wins (spec BK2);
  - «Preparar reserva» (Code, citas.js);
  - «¿Qué consulta?» (Switch);
  - **Changed in R1, approved by the human (2026-11-22): two queries instead of three.** `prepare()` asks for
    `agenda` (the patient's next appointment **and**, when a type is known, its slots) or `book`.
    So «Mi próxima cita» and «Buscar huecos» become one node, **«Consultar agenda»**. The
    original plan, kept for reference:
  - «Mi próxima cita», «Buscar huecos» and «Reservar» (Postgres on `Neon main`, each with an
    error output). Each returns **exactly one row**:
    - «Mi próxima cita» and «Buscar huecos» use `json_agg` or a `LEFT JOIN` on one row, so 0
      slots still give one item;
    - «Reservar» returns the booking result, plus the next slots when the result is `taken` or
      `invalid`, plus the existing appointment when it is `limit`, in one statement;
  - «Componer reserva» (Code, citas.js);
  - «Responder reserva» (Telegram). Its `inlineKeyboard` is a **single expression** that builds
    `{ rows: [{ row: { buttons: [{ text, additionalFields: { callback_data } }] } }] }` from
    «Componer reserva»'s rows (Step 0).
    - **Replaced in R6 (human, 2026-11-22).** n8n drops a string expression in place of a whole
      `fixedCollection`, so the message went out with no buttons. «Componer reserva» still
      outputs `inlineKeyboard` (`toTelegramKeyboard`). The Switch **«¿Cuántos botones?»** (rules
      `rows.length === 1…5`) sends it to **«Responder reserva (1)» … «(5)»**. Each of these has
      N fixed rows, and each button reads its `text` and `callback_data` with its own
      expression, such as `{{ $json.inlineKeyboard.rows[0].row.buttons[0].text }}`.
  - «Responder con pedir cita» (Telegram), with the «Pedir cita» button (`bk:menu`);
- **changed:**
  - «Clasificar» and «Decidir» carry the extended consentimiento.js;
  - «¿Qué ha llegado?» sends `booking_button` with the consent buttons (answerQuery first) and
    `booking_command` with the commands;
  - «¿Qué hacer?» gains the `booking` output, and its `core` output goes through «¿Es una
    reserva?»;
  - «Componer respuesta» sets `keyboard: 'offer'` when `offer_booking` is true;
  - «¿Qué teclado?» gains `offer` and `booking`.
- **Unchanged:** everything else, and the settings (C21, BK22).

**Pinned runs** (approved A4 extension; fake ids `900301…`; one run per scenario). With consent:

- `/cita` with no appointment → menu;
- `/cita` with one → limit;
- `/micita` with and without an appointment;
- a phrase with a type → slots;
- a request-only phrase → request text;
- a negative phrase → B;
- «Otro tratamiento» → request text;
- type → slots;
- no slots;
- «Ver más»;
- slot → confirmation;
- «Confirmar» → `booked`, then `taken` + slots, `invalid` + slots, `limit` + appointment;
- a malformed `bk:` → menu;
- a Neon error on each of the three queries → D7;
- an answer with `offer_booking` → «Pedir cita».

Without consent: `/cita`, `/micita`, a `bk:` button and a phrase → the notice.

Each run checks the path, the text, the keyboard rows (each `callback_data` ≤ 64 bytes) and the
chat id, and that **B is called only in the "negative phrase" and `offer_booking` runs**.

**Afterwards:**

1. `saveManualExecutions: false`, read back;
2. **no pinned data** in A or B, checked with `get_workflow_details` and with a CLI export;
3. the list of executions for the human to delete.

## Step 6: Publish and test from Telegram [human] (BK7)

The human publishes **B first, then A**, then sends the spec's Telegram acceptance messages.

The agent checks:

- `agenda_appointments` on `main`, read-only: status, type and times, never the subject;
- B's executions: none for booking steps, and only `question` in the others;
- that «Responder reserva» sent the dynamic keyboard. If not, the fallback is one Telegram node
  per keyboard shape (menu, 1–3 slots, confirmation, request-only).
  - **It did not.** The human chose a generic version of the fallback: one node per **number of
    buttons** (1–5), not per shape, so no new shape needs a new node. See Step 5.

## Step 7: Exports and docs (BK27)

- Export A and B with the `shared` block removed, and run the scan.
- Run the three Node tests (citas, consentimiento, urgencias) and the two SQL test files, all
  green with their sync checks.
- README: a "Booking (SPEC-007)" subsection with `/cita`, «Pedir cita», `/micita`, the flow, and
  the limitations; and the "Try it" rows.
- `specs/index.md`.

## Requirement → component map

| Requirement | Component |
|---|---|
| BK1, BK8, BK18 | consentimiento.js (`cita`, `micita`, `booking`), «Preparar reserva», «Mi próxima cita» |
| BK2–BK4 | «Detectar urgencia» → «Decidir» → «¿Es una reserva?» (`detectBookingPhrase`) |
| BK5–BK7 | B "Validar y componer" + "Resultado"; «Componer respuesta» → «Responder con pedir cita» |
| BK9–BK14 | `prepare` / `compose`, «Consultar agenda», «¿Cuántos botones?» → «Responder reserva (1)…(5)», the codec |
| BK15–BK17 | «Reservar» → `agenda_book` (SPEC-004 constraints), `compose` |
| BK19 | `004_booking.sql`, `test_booking_sql.py` |
| BK20 | the error outputs of the three queries → D7 |
| BK21, BK22 | no booking path through B; A's settings; no new table |
| BK23 | `citas.test.js`, `consentimiento.test.js`, `evals/booking_phrases.yaml` |
| BK24–BK27 | Steps 0, 2–7 |
