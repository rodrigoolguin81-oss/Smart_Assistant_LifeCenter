---
type: tasks
spec_id: SPEC-003
title: urgencies — Task Breakdown
description: Ordered, test-first tasks to build the urgency detector (JS, dataset, Node test), add it to the n8n demo workflow, test it from Telegram and close it with the clinical review.
tags: [tasks, urgencies, SPEC-003]
status: implemented
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-19T00:00:00Z }
verified: { by: human, at: 2026-11-19T00:00:00Z }
stale_after: null
---

# urgencies — Tasks

Same order as CHG-001:

1. JS, dataset and test, until the test is green.
2. The node in n8n, tested with pinned data.
3. The human publishes and tests from Telegram.

The workflow is not touched before U2 is done. Steps marked **[humano]** need the human. Nothing is
committed unless the human asks.

- [x] U0: Dataset and test first (red).
  - Done 2026-11-19. The dataset has 52 items: 30 symptom messages (8 `severe` covering A1, 22
    `urgent`) and 22 `none`, including the pair "¿la limpieza duele?" / "la limpieza duele".
  - Red for the expected reason: the dataset shape, the phone constant and the three fixed texts
    pass. Only the missing `isQuestion`, `normalize`, `detectUrgency` and `composeUrgencyReply`
    fail (5 checks). The sync check is skipped because the node does not exist yet.
  - Write `evals/urgency_dataset.yaml`: 30 symptom messages (at least 5 `severe`, covering every A1
    sign) and about 20 `none` messages, per the plan. Include the equivalent pair with and without
    question marks.
  - Write `n8n/code/urgencias.test.js`: subset-YAML reader, unit checks, dataset report and sync
    check.
  - Create `n8n/code/urgencias.js` with only the constants and texts. Run the test.
  - Check: the test runs and fails on the missing detector, not on the dataset format.
  - Covers: U17, U18.
- [x] U1: Detector (green).
  - Implement `isQuestion` (on the raw text, before `normalize`), `normalize`, the rule tables,
    `detectUrgency` and `composeUrgencyReply` in
    `urgencias.js`.
  - Adjust the rules (never the labels, unless a label is wrong) until every dataset item matches.
  - Check: `node n8n/code/urgencias.test.js` is green with NFR-04 30/30, every severe item
    `severe`, 0 false positives and 0 false negatives on the dataset. Paste the report here, and
    record any rule change.
  - Covers: U2, U5–U13.
  - Done 2026-11-19. No dataset label was changed. Test output:

    ```text
    SKIP sync check: node "Detectar urgencia" not in the export yet

    == SPEC-003 urgency report
    NFR-04 derived: 30/30 (100.0 %)
    severe classified severe: 8/8
    false positives (none → urgent/severe): 0/22
    false negatives (symptom → none): 0
    wrong severity (urgent ↔ severe): 0

    GREEN: all checks passed
    ```

  - Differences from the plan's initial lists. All of them are additions; no rule was relaxed:
    - Figurative: `ver` and `saber` after "duele".
    - Blow: `me cai`.
    - Tooth damage: the feminine forms (`rota`, `partida`, `caida`, `suelta`, `floja`).
    - Personal markers: `tiene`, `lleva` and `sigue`, plus the forms "me cuesta / me di / me
      hicieron / me pusieron / me molesta / me hincha".
    - Hypothetical: "duele mucho el/la" and "es doloroso/a".
    - Treatment words: plurals and `brackets`.
  - Each item's result records the rule ids it fired, as `info_question`, `info_hypothetical`,
    `reported_state`, `doubt` or a `sev_*` rule. That is the `matched` field the n8n execution will
    show (U15).
- [x] U2: n8n node.
  - Done 2026-11-19, saved as the version "SPEC-003 U2: detector de urgencias" (not yet
    published).
  - Code check on a temporary export: the "Detectar urgencia" `jsCode` starts with the exact
    content of `urgencias.js`, followed only by the 7 wiring lines.
  - Connections: "Seudonimizar → Detectar urgencia → ¿Es urgencia?". `true` goes to "¿Ofrecer
    recepción?" and `false` to "Buscar en kb".
  - Pinned run (execution 54), 5 messages:
    - "se me ha hinchado la cara y me cuesta tragar" → `severe` (`sev_breath_swallow`);
    - "Me llamo [NOMBRE] y me sangra mucho la encía desde ayer" → `urgent` (`sym_bleeding`,
      `reported_state`).

    Both went straight to "¿Ofrecer recepción?" → "Responder con botón" with the fixed text, the
    `000 000 000` phone and the example notice.
  - The 3 `none` messages ("¿Cuánto cuesta una limpieza?", "¿la limpieza duele?", "me duele
    pensar en el precio de la limpieza") were the only items in "Buscar en kb" and "Gemini", and
    went through "Validar y componer" as in CHG-001.
  - Via MCP, add "Detectar urgencia" (file content plus wiring) and "¿Es urgencia?", and rewire
    them between "Seudonimizar" and "Buscar en kb", per the plan.
  - Check: a pinned run where urgency items reach "Responder con botón" without running "Buscar en
    kb" or "Gemini", and a normal item follows the CHG-001 path. The node's `jsCode` starts with
    the file's exact content.
  - Covers: U1, U3, U4, U15, U16.
- [x] U3 **[humano]**: Publish and test from Telegram.
  - Done 2026-11-19 with the published version. Executions reviewed by the agent:
    - Urgencies (no "Buscar en kb" or "Gemini"):
      - 55, "me sangra mucho la encia desde ayer" → `urgent`;
      - 56, "se me ha hinchado la cara y me cuesta tragar" → `severe`;
      - 61, "desde el lunes me molesta mucho una muela" → `urgent` (`sym_pain`,
        `reported_state`), a message outside the dataset.
    - Normal path:
      - 57, "¿cuánto dura una ortodoncia?" → Gemini abstained;
      - 58, "la limpieza duele?" → a question; Gemini abstained;
      - 59, "me duele pensar en el precio de la limpieza" → 60 € with TAR-001;
      - 60, "me sale muy caro el precio" → `below_threshold`;
      - 62, "tengo una cita el lunes" → Gemini abstained.
  - Not run in that session: tapping the button after an urgency reply, and the CHG-001
    regression messages.
  - Completed later the same day:
    - execution 64, "me duele mucho una muela" → `urgent`;
    - executions 70 and 71, the button → D8 text;
    - executions 65–69, the CHG-001 messages: limpieza 60 €, sábados HOR-001, Sanitas
      `below_threshold`, name and phone with placeholders in the Gemini body (280 €), injection
      `model_abstained`.
  - Execution 63 (limpieza) had ended in a Gemini `api_error` before that: a free-tier failure,
    handled by the D7 path.
  - Send the spec's acceptance messages, tap the button, and repeat the CHG-001 regression
    messages. The agent reviews the executions.
  - Covers: all acceptance criteria except the export and the clinical review.
- [x] U4: Export and docs.
  - Done 2026-11-19. The export has 18 nodes and matches the published version, with no
    `pinData`. The `shared` block was removed and the secret and personal-data scan is clean.
  - The test's sync check now runs against the export and passes: GREEN, NFR-04 30/30, severe
    8/8, 0 false positives, 0 false negatives.
  - README "Demo" section updated:
    - the diagram, with the urgency branch;
    - urgency rows in "Try it";
    - how to set the real phone;
    - the urgency limitations, and the privacy note (SPEC-003 is in place, but real patients are
      still blocked).
  - `specs/index.md` updated.
  - Re-export to `n8n/workflows/lifecenter-telegram-demo.json` with the `shared` block removed.
  - Run the secret and personal-data scan. The test's sync check must now run and pass.
  - Update the README: urgency rows in "Try it", and the limitations and the example phone in
    "Known limitations".
  - Update `specs/index.md`.
  - Covers: U16; acceptance "re-exported…".
- [x] U5 **[humano: Prince Calderon]**: Clinical review.
  - Review the dataset, the fixed texts and the severe list (A1–A3).
  - Record the result in clarifications, or record it as still pending. SPEC-003 can be marked
    implemented with the review pending, but opening to real patients stays blocked (clarifications,
    "Dependencies and conditions").
  - Covers: U19.
  - 2026-11-19: the human records the review as **pending** (see clarifications, "Clinical review
    status"). SPEC-003 may close for the demo with it pending; opening to real patients stays
    blocked.
