---
type: plan
spec_id: SPEC-003
title: urgencies — Technical Plan
description: Design of the deterministic urgency detector (normalization, rules, levels), its JS source and Node test against the urgency dataset, and the two nodes added to the n8n demo workflow between Seudonimizar and Buscar en kb.
tags: [plan, urgencies, SPEC-003, n8n]
status: implemented
sources: [./spec.md, ./clarifications.md, ../003-n8n-migration/plan.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# urgencies — Plan

## Architecture

```text
Telegram Trigger → ¿Qué ha llegado? ─Texto→ Seudonimizar
  → Code: Detectar urgencia          (n8n/code/urgencias.js + wiring)
  → IF: ¿Es urgencia?  (reason === 'urgency')
       ├─ true  → ¿Ofrecer recepción? → Responder con botón     (existing nodes)
       └─ false → Buscar en kb → … (CHG-001 path, unchanged)
```

Two nodes are added and one connection is moved: "Seudonimizar → Buscar en kb" becomes
"Seudonimizar → Detectar urgencia → ¿Es urgencia? (false) → Buscar en kb". An urgency item reaches
"¿Ofrecer recepción?" with `handoff: true`, so it gets the existing "Responder con botón" node
(HTML-escaped text plus the "Hablar con recepción" button). Tapping the button already goes to the
D8 branch (U14). "Buscar en kb" reads `$json.question`, which passes through unchanged when
`level` is `none`. Later nodes read `$('Seudonimizar').item`, so they are unaffected.

## Source file: `n8n/code/urgencias.js`

A plain script with no `require`, `module` or `export`, so it can be pasted into the Code node as
is. It defines, in this order:

1. **Configuration constants** (U13), at the very top:
   - `URGENCY_PHONE = '000 000 000'`;
   - `URGENCY_PHONE_IS_EXAMPLE = true`.
2. **Fixed texts:** `URGENT_MESSAGE`, `SEVERE_MESSAGE` and `EXAMPLE_PHONE_NOTICE`, verbatim from
   the spec. The phone is inserted from the constant.
3. `isQuestion(text)` and `normalize(text)`, described below.
4. The rule tables: `SEVERE_RULES`, `SYMPTOM_TERMS`, `FIGURATIVE`, `PERSONAL_MARKERS`,
   `HYPOTHETICAL` and `TREATMENT_WORDS`. Each rule has an `id` and a regex over the normalized
   text.
5. `detectUrgency(text)`, which takes the pseudonymized text as it arrives, computes
   `isQuestion` and `normalize` itself, and returns `{ level, matched, question }`. `matched` is the list of rule ids
   that fired (U15).
6. `composeUrgencyReply(level)`, which returns the reply text (U11, U12).

The Code node "Detectar urgencia" (Run once for each item) is the file's content followed by this
wiring, and nothing else (U16):

```js
const r = detectUrgency($json.question);
if (r.level === 'none') return { json: { ...$json, urgency_level: 'none' } };
return { json: {
  chatId: $json.chatId, text: composeUrgencyReply(r.level), handoff: true,
  reason: 'urgency', urgency_level: r.level, matched: r.matched,
} };
```

### Question flag and normalization (U10)

`isQuestion(text)` is computed on the **raw** pseudonymized text, **before** normalization
removes the punctuation. It is `true` if the text contains `¿` or `?`. The flag is passed to the
classification (informational question, step 4 below) and returned in the result for the
execution record.

`normalize` runs on the **already pseudonymized** question, which is the input of the node:

1. Lowercase.
2. Remove accents: decompose to NFD and drop the combining marks (`\p{M}`). `ñ` becomes `n`, which
   is harmless for these rules.
3. Replace the SPEC-001 placeholders (`[nombre]`, `[telefono]`, `[dni]`, `[email]`, once
   lowercased) with a space.
4. Replace every character other than a letter, digit or space with a space. This covers `¿?¡!.,;:`
   and quotes.
5. Collapse repeated whitespace into one space, and trim.

All rules are written against this normalized form: lowercase, no accents, single spaces.

### Classification (U5–U9)

Steps, applied in order to the normalized text:

1. **Remove figurative phrases** (U8). Each `FIGURATIVE` pattern that matches is cut from the text
   and recorded in `matched`, and classification continues on what remains:
   - a pain verb followed by an infinitive, by `que` or by money words: `me duele (pensar|pagar|
     gastar|tener que|que) …`, `duele (el bolsillo|la cartera)`;
   - `de golpe`;
   - `me muero de (ganas|risa)`.
2. **Severe** (U6): if any `SEVERE_RULES` pattern matches, the result is `severe`. These are
   provisional (clarifications A1):
   - `(no puedo|me cuesta|dificultad para|no consigo) (respirar|tragar)`;
   - swelling (`hinch*|inflam*`) together with `(cuello|ojo|no puedo abrir)`;
   - bleeding (`sangr*`) together with `(no para|no deja de|sin parar|no se corta|a chorro)`;
   - a blow (`golpe|caida|me cai|accidente|traumatismo`) together with `(cara|cabeza|mandibula)`,
     or with `(desmay|perdi el conocimiento|inconsciente)`, or with a knocked-out tooth
     (`se me ha caido|arrancado`);
   - `fiebre` together with swelling.
3. **Symptom term** (A3). If no `SYMPTOM_TERMS` pattern matches, the result is `none`. The initial
   list is extended with the dataset:
   - pain: `dolor`, `duele`, `duelen`, `doler`, `molest*`, `pinchazo`;
   - bleeding: `sangr*`;
   - swelling: `hinch*`, `inflam*`;
   - `fiebre`, `pus`, `absceso`, `flemon`, `infecc*`;
   - `golpe`, `traumatismo`;
   - a tooth or restoration (`diente`, `muela`, `corona`, `empaste`, `funda`, `puente`) together
     with `(roto|rota|partido|partida|se ha caido|se me ha caido|se mueve|suelto|flojo|movido)`.
4. **Informational question** (U7). The result is `none` only if all three hold:
   - no `PERSONAL_MARKERS` pattern matches;
   - a `TREATMENT_WORDS` pattern matches (`limpieza|blanqueamiento|ortodoncia|implante|
     endodoncia|extraccion|empaste|tratamiento|anestesia|revision|radiografia`);
   - `isQuestion` is `true` (the raw text had `¿` or `?`), or a `HYPOTHETICAL` pattern matches
     (`me va a doler`, `va a doler`, `dolera`, `es doloroso`, `duele mucho la`).

   `PERSONAL_MARKERS` are the signs of a current or recent own state:
   - `me (duele|duelen|sangra|sangran|ha|he|han|esta|estan|noto|sale)`, `mi `;
   - `tengo`, `estoy`, `se me`, `llevo`;
   - `desde (ayer|hace|esta|el)`, `hoy`, `anoche`, `ahora`;
   - `despues de` together with a past form (`me hicieron`, `me han hecho`).

   A hypothetical pattern takes precedence over `me`. For example, "¿me va a doler la limpieza?"
   is `none`.
5. **Otherwise** the result is `urgent`. This covers a symptom reported as the patient's own state
   and any doubtful case (U9). Without `¿`/`?` and without a hypothetical form, a sentence such as
   "la limpieza duele" cannot be told apart from a complaint, so it is derived. The dataset
   records this pair (with and without question marks).

The rule lists are a starting point. The dataset decides: every dataset case that fails is fixed by
adjusting a rule, never by editing the label, unless the label itself was wrong. Every rule change
is recorded in the tasks.

## Dataset: `evals/urgency_dataset.yaml`

The format is a strict YAML subset, so the Node test can read it without dependencies:

```yaml
# comment lines allowed
- text: "me sangra mucho la encia desde ayer"
  expected: urgent        # urgent | severe | none
  note: "US-003 scenario"  # optional
```

Each item is exactly `- text: "…"` followed by `expected:` and an optional `note:`. Values are
double-quoted, with `\"` allowed. The test fails with the line number on anything else.

Content:

- **30 symptom messages:**
  - at least 5 `severe`, covering every A1 sign;
  - the rest `urgent`: the US-003 scenario, post-treatment symptoms, lowercase without accents,
    typos within the normalization (accents, case, spacing), and a symptom message with
    `[NOMBRE]`/`[TELEFONO]` placeholders.
- **About 20 normal messages (`none`):**
  - treatment and aftercare questions ("¿la limpieza duele?", "¿me va a doler el blanqueamiento?",
    "¿qué cuidados hay después de la limpieza?");
  - figurative uses ("me duele pensar en el precio", "tengo una cita el lunes", "me lo dijeron de
    golpe");
  - ordinary questions (prices, schedules, insurance, the CHG-001 acceptance messages).
- **One equivalent pair with and without question marks:** "¿la limpieza duele?" (`none`) and
  "la limpieza duele" (`urgent`, by doubt). It shows that the question flag is read before the
  punctuation is removed.

## Test: `n8n/code/urgencias.test.js`

Run with `node n8n/code/urgencias.test.js`. It uses no dependencies and exits non-zero on failure.

- It loads `urgencias.js` with `new Function(source + 'return {…}')`, the same technique used in
  CHG-001, so the file stays paste-ready.
- **Unit checks:**
  - `normalize` (case, accents, punctuation, repeated spaces, placeholders);
  - `isQuestion` on the raw text (`¿…?`, only `?`, none);
  - the composed texts, compared exactly with the spec's texts, with and without the
    example-phone notice;
  - that no reply contains any of the input's words.
- **Dataset:** every item must get its `expected` level. The report prints:
  - NFR-04: derived / 30, required 30/30;
  - severe correct / number of severe items;
  - false positives: `none` items classified `urgent` or `severe`, each listed;
  - false negatives, each listed.

  The test is green only if every label matches. Its output is pasted into the task when it is
  closed.
- **Sync check (U16):** if `n8n/workflows/lifecenter-telegram-demo.json` contains a node named
  "Detectar urgencia", its `jsCode` must start with the exact content of `urgencias.js`. Before the
  node exists, this check is skipped and the test says so.

## Workflow changes (MCP `update_workflow`, after the plan is approved)

1. Add "Detectar urgencia" (Code, per item) with the file content plus the wiring above, and the
   IF "¿Es urgencia?" (`{{ $json.reason }}` equals `urgency`).
2. Remove "Seudonimizar → Buscar en kb". Add "Seudonimizar → Detectar urgencia → ¿Es urgencia?".
   Wire `true` to "¿Ofrecer recepción?" and `false` to "Buscar en kb".
3. Move the downstream nodes on the canvas to make room. No other node changes.

## Verification

1. **Node test green** (dataset plus unit checks).
2. **Pinned run in n8n** (MCP `test_workflow`), with Postgres, Gemini and Telegram pinned:
   - a few urgent, severe and normal items;
   - urgency items must not run "Buscar en kb" or "Gemini";
   - a normal item must follow the CHG-001 path.
3. **[humano] Publish and test from Telegram:**
   - the spec's acceptance messages;
   - the CHG-001 regression messages;
   - the button.

   The agent reviews the executions.
4. **Export** to `n8n/workflows/` with the `shared` block removed, then the secret and personal-data
   scan (CHG-001 procedure). The Node test's sync check then passes against the export.

## Requirement → component map

| Requirement | Component |
|---|---|
| U1, U3, U4 | Workflow wiring (Detectar urgencia, ¿Es urgencia?) |
| U2, U5–U10 | `normalize`, rule tables and `detectUrgency` in `urgencias.js` |
| U11–U13 | Constants, texts and `composeUrgencyReply`; existing "Responder con botón" |
| U14 | Existing D8 branch (CHG-001) |
| U15 | Node output: `reason`, `urgency_level`, `matched` |
| U16 | Node `jsCode` = file + wiring; sync check in the test |
| U17 | `evals/urgency_dataset.yaml` |
| U18 | `urgencias.test.js` report |
| U19 | Human review task (tasks) |
