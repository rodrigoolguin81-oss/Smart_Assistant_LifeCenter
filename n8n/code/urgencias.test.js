// SPEC-003 tests for n8n/code/urgencias.js (specs/004-urgencies/plan.md "Test").
// Run: node n8n/code/urgencias.test.js   — no dependencies; exits non-zero on any failure.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_PATH = path.join(__dirname, 'urgencias.js');
const DATASET_PATH = path.join(ROOT, 'evals', 'urgency_dataset.yaml');
const EXPORT_PATH = path.join(ROOT, 'n8n', 'workflows', 'lifecenter-telegram-demo.json');
const NODE_NAME = 'Detectar urgencia';
const LEVELS = ['urgent', 'severe', 'none'];

// Spec texts, typed here independently of the source so any drift fails the test (U11–U13).
const PHONE = '000 000 000';
const SPEC_URGENT =
  `No puedo valorar síntomas por aquí. Llama a la clínica al ${PHONE}. ` +
  'Si es grave o tienes dificultad para respirar, llama al 112.';
const SPEC_SEVERE =
  'Si tienes dificultad para respirar o tragar, una hemorragia que no para o te has dado un golpe ' +
  'fuerte en la cara o la cabeza, llama ahora al 112. No puedo valorar síntomas por aquí. ' +
  `Si no es una emergencia, llama a la clínica al ${PHONE}.`;
const SPEC_NOTICE = '(Este teléfono es de ejemplo: todavía no tenemos el número real de la clínica.)';

// --- Load the paste-ready source the same way n8n runs it: as a plain script body. ---
// Line endings normalized to LF: a Windows checkout (core.autocrlf) must still match the node code.
const source = fs.readFileSync(SOURCE_PATH, 'utf8').replace(/\r\n/g, '\n');
const EXPORTED = ['URGENCY_PHONE', 'URGENCY_PHONE_IS_EXAMPLE', 'URGENT_MESSAGE', 'SEVERE_MESSAGE',
  'EXAMPLE_PHONE_NOTICE', 'isQuestion', 'normalize', 'detectUrgency', 'composeUrgencyReply'];
const M = new Function(
  source + '\nreturn {' + EXPORTED.map((n) => `${n}: typeof ${n} === 'undefined' ? undefined : ${n}`).join(', ') + '};',
)();

// --- Strict YAML-subset reader for the dataset (plan "Dataset"). ---
function readDataset(file) {
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  const items = [];
  const quoted = (raw, lineNo) => {
    const m = /^"((?:[^"\\]|\\.)*)"$/.exec(raw.trim());
    if (!m) throw new Error(`${path.basename(file)}:${lineNo}: expected a double-quoted value`);
    return m[1].replace(/\\(.)/g, '$1');
  };
  lines.forEach((line, i) => {
    const n = i + 1;
    if (/^\s*(#.*)?$/.test(line)) return;
    let m;
    if ((m = /^- text: (.*)$/.exec(line))) items.push({ text: quoted(m[1], n), line: n });
    else if ((m = /^ {2}expected: (\w+)\s*(#.*)?$/.exec(line)) && items.length && !items[items.length - 1].expected) {
      if (!LEVELS.includes(m[1])) throw new Error(`${path.basename(file)}:${n}: unknown level "${m[1]}"`);
      items[items.length - 1].expected = m[1];
    } else if ((m = /^ {2}note: (.*)$/.exec(line)) && items.length) items[items.length - 1].note = quoted(m[1], n);
    else throw new Error(`${path.basename(file)}:${n}: unexpected line: ${line}`);
  });
  for (const it of items) if (!it.expected) throw new Error(`${path.basename(file)}:${it.line}: missing expected`);
  return items;
}

let failures = 0;
function check(name, fn) {
  try { fn(); } catch (e) { failures++; console.log(`FAIL ${name}: ${e.message}`); }
}
function eq(actual, expected, what) {
  if (actual !== expected) throw new Error(`${what}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}
function requireFn(name) {
  if (typeof M[name] !== 'function') throw new Error(`${name} is not implemented in urgencias.js`);
  return M[name];
}

// --- Dataset shape (U17) ---
const dataset = readDataset(DATASET_PATH);
const symptom = dataset.filter((d) => d.expected !== 'none');
const severe = dataset.filter((d) => d.expected === 'severe');
const normal = dataset.filter((d) => d.expected === 'none');
check('dataset: 30 symptom messages', () => eq(symptom.length, 30, 'symptom count'));
check('dataset: at least 5 severe', () => { if (severe.length < 5) throw new Error(`only ${severe.length}`); });
check('dataset: about 20 normal messages', () => { if (normal.length < 18) throw new Error(`only ${normal.length}`); });
check('dataset: question-mark pair present', () => {
  const pair = dataset.filter((d) => ['¿la limpieza duele?', 'la limpieza duele'].includes(d.text));
  eq(pair.length, 2, 'pair items');
});

// --- Configuration and fixed texts (U11–U13) ---
check('phone constant', () => { eq(M.URGENCY_PHONE, PHONE, 'URGENCY_PHONE'); eq(M.URGENCY_PHONE_IS_EXAMPLE, true, 'URGENCY_PHONE_IS_EXAMPLE'); });
check('fixed texts', () => { eq(M.URGENT_MESSAGE, SPEC_URGENT, 'URGENT_MESSAGE'); eq(M.SEVERE_MESSAGE, SPEC_SEVERE, 'SEVERE_MESSAGE'); eq(M.EXAMPLE_PHONE_NOTICE, SPEC_NOTICE, 'EXAMPLE_PHONE_NOTICE'); });
check('composeUrgencyReply', () => {
  const compose = requireFn('composeUrgencyReply');
  eq(compose('urgent'), `${SPEC_URGENT}\n\n${SPEC_NOTICE}`, 'urgent reply');
  eq(compose('severe'), `${SPEC_SEVERE}\n\n${SPEC_NOTICE}`, 'severe reply');
});

// --- Question flag and normalization (U10) ---
check('isQuestion on the raw text', () => {
  const isQuestion = requireFn('isQuestion');
  eq(isQuestion('¿la limpieza duele?'), true, '¿…?');
  eq(isQuestion('la limpieza duele?'), true, 'only ?');
  eq(isQuestion('la limpieza duele'), false, 'no marks');
});
check('normalize', () => {
  const normalize = requireFn('normalize');
  eq(normalize('¿Me DUELE   la muéla!!'), 'me duele la muela', 'case, accents, punctuation, spaces');
  eq(normalize('  Hinchazón\ten   el  cuello. '), 'hinchazon en el cuello', 'tabs and trim');
  eq(normalize('Me llamo [NOMBRE], mi teléfono es [TELEFONO]'), 'me llamo mi telefono es', 'placeholders');
  eq(normalize('[DNI] y [EMAIL]'), 'y', 'other placeholders');
});

// --- Dataset classification (NFR-04, U5–U9, U18) ---
let results = null;
check('detectUrgency over the dataset', () => {
  const detect = requireFn('detectUrgency');
  results = dataset.map((d) => ({ ...d, got: detect(d.text) }));
  for (const r of results) {
    if (!r.got || !LEVELS.includes(r.got.level) || !Array.isArray(r.got.matched) || typeof r.got.question !== 'boolean') {
      throw new Error(`line ${r.line}: result must be { level, matched[], question }`);
    }
  }
  const mismatches = results.filter((r) => r.got.level !== r.expected);
  if (mismatches.length) throw new Error(`${mismatches.length} dataset items with the wrong level (see report)`);
});
check('replies never echo the message (U12)', () => {
  if (!results) throw new Error('no results');
  const compose = requireFn('composeUrgencyReply');
  for (const r of results.filter((x) => x.got.level !== 'none')) {
    const reply = compose(r.got.level);
    if (![`${SPEC_URGENT}\n\n${SPEC_NOTICE}`, `${SPEC_SEVERE}\n\n${SPEC_NOTICE}`].includes(reply)) {
      throw new Error(`line ${r.line}: reply is not one of the fixed texts`);
    }
  }
});

// --- Sync with the exported workflow (U16) ---
check('n8n node carries this exact code', () => {
  if (!fs.existsSync(EXPORT_PATH)) { console.log('SKIP sync check: no export'); return; }
  const wf = JSON.parse(fs.readFileSync(EXPORT_PATH, 'utf8'));
  const nodes = (Array.isArray(wf) ? wf[0] : wf).nodes;
  const node = nodes.find((n) => n.name === NODE_NAME);
  if (!node) { console.log(`SKIP sync check: node "${NODE_NAME}" not in the export yet`); return; }
  if (!node.parameters.jsCode.startsWith(source)) throw new Error(`"${NODE_NAME}" jsCode does not start with urgencias.js`);
});

// --- Report ---
console.log('\n== SPEC-003 urgency report');
if (results) {
  const derived = results.filter((r) => r.expected !== 'none' && r.got.level !== 'none');
  const severeOk = results.filter((r) => r.expected === 'severe' && r.got.level === 'severe');
  const fp = results.filter((r) => r.expected === 'none' && r.got.level !== 'none');
  const fn = results.filter((r) => r.expected !== 'none' && r.got.level === 'none');
  const wrongLevel = results.filter((r) => r.expected !== 'none' && r.got.level !== 'none' && r.got.level !== r.expected);
  console.log(`NFR-04 derived: ${derived.length}/${symptom.length} (${((100 * derived.length) / symptom.length).toFixed(1)} %)`);
  console.log(`severe classified severe: ${severeOk.length}/${severe.length}`);
  console.log(`false positives (none → urgent/severe): ${fp.length}/${normal.length}`);
  fp.forEach((r) => console.log(`  FP line ${r.line} → ${r.got.level} [${r.got.matched.join(', ')}]: ${r.text}`));
  console.log(`false negatives (symptom → none): ${fn.length}`);
  fn.forEach((r) => console.log(`  FN line ${r.line} [${r.got.matched.join(', ')}]: ${r.text}`));
  console.log(`wrong severity (urgent ↔ severe): ${wrongLevel.length}`);
  wrongLevel.forEach((r) => console.log(`  LV line ${r.line} expected ${r.expected}, got ${r.got.level} [${r.got.matched.join(', ')}]: ${r.text}`));
} else {
  console.log(`dataset: ${dataset.length} items (${symptom.length} symptom, ${severe.length} severe, ${normal.length} none) — detector not run`);
}
console.log(failures ? `\nRED: ${failures} check(s) failed` : '\nGREEN: all checks passed');
process.exit(failures ? 1 : 0);
