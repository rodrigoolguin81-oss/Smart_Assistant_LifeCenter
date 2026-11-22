// SPEC-007 tests for n8n/code/citas.js (specs/008-booking/plan.md Step 1).
// Run: node n8n/code/citas.test.js   — no dependencies; exits non-zero on any failure.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_PATH = path.join(__dirname, 'citas.js');
const DATASET_PATH = path.join(ROOT, 'evals', 'booking_phrases.yaml');
const EXPORT_PATH = path.join(ROOT, 'n8n', 'workflows', 'lifecenter-telegram-demo.json');
const NODE_NAMES = ['¿Es una reserva?', 'Preparar reserva', 'Componer reserva'];

// Spec texts (spec.md "Fixed texts", approved 2026-11-22), typed here independently of the source.
const T = {
  TYPE_MENU: '¿Qué tipo de cita quieres?',
  REQUEST_ONLY: 'Ese tratamiento necesita una valoración previa en la clínica. Puedo reservarte una primera visita, o puedes hablar con recepción.',
  SLOTS: 'Estos son los primeros huecos para {tipo}:',
  MORE_SLOTS: 'Estos son los siguientes huecos para {tipo}:', // human, R6 (2026-11-22)
  NO_SLOTS: 'Ahora mismo no hay huecos libres para {tipo} en los próximos 30 días. Llama a recepción para buscar otra fecha.',
  CONFIRM: 'Vas a reservar {tipo} el {fecha} a las {hora}. ¿Lo confirmo?',
  BOOKED: 'Hecho: tienes {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, de momento llama a recepción.',
  TAKEN: 'Ese hueco se acaba de ocupar. Estos son los siguientes:',
  UNAVAILABLE: 'Ese hueco ya no está disponible. Estos son los siguientes:',
  LIMIT: 'Ya tienes {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, llama a recepción.', // human, 2026-11-22
  MY_APPOINTMENT: 'Tu próxima cita: {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, llama a recepción.',
  NO_APPOINTMENT: 'No tienes ninguna cita reservada. Escribe /cita para pedir una.',
  ERROR: 'Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?', // CHG-001 D7
};
const LABELS = {
  pedir: 'Pedir cita', mas: 'Ver más', confirmar: 'Confirmar', otroHueco: 'Elegir otro hueco',
  otroTratamiento: 'Otro tratamiento', recepcion: 'Hablar con recepción', primeraVisita: 'Primera visita',
};

// --- Load the paste-ready source the same way n8n runs it: as a plain script body. ---
const source = fs.readFileSync(SOURCE_PATH, 'utf8').replace(/\r\n/g, '\n');
const EXPORTED = ['TEXTS', 'LABELS', 'TYPE_NAMES', 'BOOKABLE_TYPES', 'REQUEST_ONLY_TYPES', 'encodeSlot', 'decodeSlot',
  'cb', 'parseBookingCallback', 'detectBookingPhrase', 'bookingPhraseFor', 'shortLabel', 'longDate', 'hourOf', 'prepare', 'compose',
  'toTelegramKeyboard'];
const M = new Function(
  source + '\nreturn {' + EXPORTED.map((n) => `${n}: typeof ${n} === 'undefined' ? undefined : ${n}`).join(', ') + '};',
)();

let failures = 0;
function check(name, fn) {
  try { fn(); } catch (e) { failures++; console.log(`FAIL ${name}: ${e.message}`); }
}
function eq(actual, expected, what) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a !== b) throw new Error(`${what}: expected ${b}, got ${a}`);
}
function requireFn(name) {
  if (typeof M[name] !== 'function') throw new Error(`${name} is not implemented in citas.js`);
  return M[name];
}

// --- Fixed data: "now" is Friday 4 Dec 2026, 07:00 Madrid; slots on Monday 7 and Tuesday 8 ---
const NOW = '2026-12-04T06:00:00.000Z';
const S1 = '2026-12-07T08:00:00.000Z'; // lun 7 dic 9:00 Madrid (UTC+1)
const S2 = '2026-12-07T15:00:00.000Z'; // lun 7 dic 16:00
const S3 = '2026-12-08T08:00:00.000Z'; // mar 8 dic 9:00
const end = (iso, min) => new Date(Date.parse(iso) + min * 60000).toISOString();
const code = (iso) => Math.round(Date.parse(iso) / 60000).toString(36); // independent of the source
const slot = (iso, min = 45) => ({ starts_at: iso, ends_at: end(iso, min) });
const btn = (text, data) => ({ text, data });
const RECEPCION = [btn(LABELS.recepcion, 'handoff')];
const MENU_ROWS = [
  [btn('Revisión', 'bk:t:revision')], [btn('Limpieza', 'bk:t:limpieza')], [btn('Primera visita', 'bk:t:primera_visita')],
  [btn(LABELS.otroTratamiento, 'bk:o')], RECEPCION,
];
const SLOT_ROWS = (type, slots) => [
  ...slots.map((s) => [btn(s.label, `bk:s:${type}:${code(s.iso)}`)]),
  [btn(LABELS.mas, `bk:m:${type}:${code(slots[slots.length - 1].iso)}`)],
  RECEPCION,
];
const THREE = [
  { iso: S1, label: 'lun 7 dic · 9:00' }, { iso: S2, label: 'lun 7 dic · 16:00' }, { iso: S3, label: 'mar 8 dic · 9:00' },
];

// === Texts and labels ===

check('fixed texts', () => {
  for (const [k, v] of Object.entries(T)) eq((M.TEXTS || {})[k], v, `TEXTS.${k}`);
});
check('button labels', () => eq(M.LABELS, LABELS, 'LABELS'));
check('types', () => {
  eq(M.TYPE_NAMES, { revision: 'Revisión', limpieza: 'Limpieza', primera_visita: 'Primera visita',
    blanqueamiento: 'Blanqueamiento', tratamiento_largo: 'Implantes, ortodoncia u otro tratamiento largo' }, 'TYPE_NAMES');
  eq(M.BOOKABLE_TYPES, ['revision', 'limpieza', 'primera_visita'], 'BOOKABLE_TYPES');
  eq(M.REQUEST_ONLY_TYPES, ['blanqueamiento', 'tratamiento_largo'], 'REQUEST_ONLY_TYPES');
});

// === Callback codec (BK12, BK13) ===

check('slot codec round trip', () => {
  const enc = requireFn('encodeSlot');
  const dec = requireFn('decodeSlot');
  for (const iso of [S1, '2027-03-29T07:00:00.000Z', '2084-12-31T23:45:00.000Z', '2099-06-01T10:15:00.000Z']) {
    eq(enc(iso), code(iso), `encode ${iso}`);
    eq(dec(enc(iso)), iso, `decode ${iso}`);
  }
  eq(dec('ZZ!'), null, 'garbage');
  eq(dec(''), null, 'empty');
});
check('every callback fits in 64 bytes (BK12)', () => {
  const make = requireFn('cb');
  const far = '2099-12-31T23:45:00.000Z';
  const all = ['menu', 'other'].map((k) => make(k));
  for (const t of Object.keys(M.TYPE_NAMES || {})) {
    all.push(make('type', t), make('retry', t));
    for (const k of ['slot', 'confirm', 'more']) all.push(make(k, t, far));
  }
  for (const d of all) {
    const n = Buffer.byteLength(String(d), 'utf8');
    if (n < 1 || n > 64) throw new Error(`"${d}" is ${n} bytes`);
  }
  eq(make('confirm', 'limpieza', S1), `bk:c:limpieza:${code(S1)}`, 'confirm format');
  eq(make('menu'), 'bk:menu', 'menu');
  eq(make('other'), 'bk:o', 'other');
  eq(make('type', 'revision'), 'bk:t:revision', 'type');
  eq(make('retry', 'revision'), 'bk:r:revision', 'retry');
  eq(make('more', 'limpieza', S3), `bk:m:limpieza:${code(S3)}`, 'more');
  eq(make('slot', 'limpieza', S1), `bk:s:limpieza:${code(S1)}`, 'slot');
});
check('parseBookingCallback', () => {
  const p = requireFn('parseBookingCallback');
  eq(p('bk:menu'), { step: 'menu', type: null, start: null }, 'menu');
  eq(p('bk:o'), { step: 'other', type: null, start: null }, 'other');
  eq(p('bk:t:limpieza'), { step: 'type', type: 'limpieza', start: null }, 'type');
  eq(p('bk:t:blanqueamiento'), { step: 'type', type: 'blanqueamiento', start: null }, 'request-only type');
  eq(p(`bk:s:limpieza:${code(S1)}`), { step: 'slot', type: 'limpieza', start: S1 }, 'slot');
  eq(p(`bk:c:revision:${code(S2)}`), { step: 'confirm', type: 'revision', start: S2 }, 'confirm');
  eq(p(`bk:m:limpieza:${code(S3)}`), { step: 'more', type: 'limpieza', start: S3 }, 'more');
  eq(p('bk:r:primera_visita'), { step: 'retry', type: 'primera_visita', start: null }, 'retry');
  const bad = { step: 'malformed', type: null, start: null };
  for (const d of ['bk:', 'bk:x', 'bk:t:no_existe', 'bk:s:limpieza', 'bk:s:limpieza:@@', `bk:c:no_existe:${code(S1)}`,
    `bk:s:blanqueamiento:${code(S1)}`, 'bk:t:limpieza:extra', 'handoff', '', undefined]) eq(p(d), bad, `malformed ${d}`);
});

// === Phrase detector (BK3, BK4; Decisions Q2) ===

function readDataset(file) {
  const items = [];
  fs.readFileSync(file, 'utf8').split(/\r?\n/).forEach((line, i) => {
    const n = i + 1;
    if (/^\s*(#.*)?$/.test(line)) return;
    let m;
    if ((m = /^- text: "((?:[^"\\]|\\.)*)"$/.exec(line))) items.push({ text: m[1], line: n });
    else if ((m = /^ {2}expected: (booking|none)$/.exec(line)) && items.length) items[items.length - 1].expected = m[1];
    else if ((m = /^ {2}type: (revision|limpieza|primera_visita|request_only)$/.exec(line)) && items.length) items[items.length - 1].type = m[1];
    else throw new Error(`${path.basename(file)}:${n}: unexpected line: ${line}`);
  });
  for (const it of items) if (!it.expected) throw new Error(`line ${it.line}: missing expected`);
  return items;
}
const dataset = readDataset(DATASET_PATH);
const positives = dataset.filter((d) => d.expected === 'booking');
const negatives = dataset.filter((d) => d.expected === 'none');
check('dataset shape', () => {
  if (positives.length < 20 || negatives.length < 20) throw new Error(`${positives.length} positives, ${negatives.length} negatives`);
  for (const must of ['tengo una cita el lunes', '¿cuánto cuesta una cita?', 'cancelar mi cita', 'cambiar mi cita']) {
    if (!negatives.some((d) => d.text === must)) throw new Error(`missing negative «${must}»`);
  }
});
let phraseReport = null;
check('detectBookingPhrase over the dataset (every positive, 0 negatives)', () => {
  const detect = requireFn('detectBookingPhrase');
  const fn = [];
  const fp = [];
  const wrongType = [];
  for (const d of dataset) {
    const r = detect(d.text);
    if (!r || typeof r.match !== 'boolean') throw new Error(`line ${d.line}: result must be { match, type, requestOnly }`);
    if (d.expected === 'booking' && !r.match) fn.push(d);
    if (d.expected === 'none' && r.match) fp.push(d);
    if (d.expected === 'booking' && r.match) {
      const got = r.requestOnly ? 'request_only' : r.type;
      if ((d.type || null) !== (got || null)) wrongType.push(`${d.text} → ${got}`);
    }
  }
  phraseReport = { fn, fp, wrongType };
  const msgs = [];
  if (fn.length) msgs.push(`missed: ${fn.map((d) => d.text).join(' | ')}`);
  if (fp.length) msgs.push(`false positives: ${fp.map((d) => d.text).join(' | ')}`);
  if (wrongType.length) msgs.push(`wrong type: ${wrongType.join(' | ')}`);
  if (msgs.length) throw new Error(msgs.join('; '));
});

// === Order: an urgency always wins over a booking phrase (BK2; human, 2026-11-22) ===
// Runs the real urgencias.js with its node wiring, then the check "¿Es una reserva?" does in A.
const urgSource = fs.readFileSync(path.join(__dirname, 'urgencias.js'), 'utf8').replace(/\r\n/g, '\n');
const U = new Function(urgSource + '\nreturn { detectUrgency, composeUrgencyReply };')();
const wiredUrgency = (question) => {
  const r = U.detectUrgency(question);
  return r.level === 'none' ? { question, urgency_level: 'none' }
    : { text: U.composeUrgencyReply(r.level), handoff: true, reason: 'urgency', urgency_level: r.level, matched: r.matched };
};
check('an urgency always wins over a booking phrase', () => {
  const forA = requireFn('bookingPhraseFor');
  const mixed = ['quiero cita, me sangra mucho la encía', 'necesito una cita urgente, se me ha hinchado la cara',
    'quiero pedir cita, me duele muchísimo una muela', 'dame cita, se me ha roto un diente'];
  const wrong = [];
  for (const text of mixed) {
    const urgency = wiredUrgency(text);
    if (urgency.urgency_level === 'none') { wrong.push(`detector missed the urgency in «${text}»`); continue; }
    if (!requireFn('detectBookingPhrase')(text).match) wrong.push(`«${text}» should look like a booking phrase on its own`);
    if (forA(text, urgency).match) wrong.push(`«${text}» went to booking despite the urgency`);
  }
  if (wrong.length) throw new Error(wrong.join('; '));
  eq(forA('quiero pedir cita', wiredUrgency('quiero pedir cita')), { match: true, type: null, requestOnly: false }, 'no urgency → booking');
  eq(forA('quiero pedir cita', null), { match: true, type: null, requestOnly: false }, 'urgency not run → phrase only');
});

// === Madrid dates (Q15), including both DST changes ===

check('shortLabel, longDate and hourOf in Europe/Madrid', () => {
  const s = requireFn('shortLabel');
  const l = requireFn('longDate');
  const h = requireFn('hourOf');
  eq(s(S1), 'lun 7 dic · 9:00', 'Monday morning');
  eq(s(S2), 'lun 7 dic · 16:00', 'Monday afternoon');
  eq(s('2027-03-26T08:00:00.000Z'), 'vie 26 mar · 9:00', 'Friday before the March change (UTC+1)');
  eq(s('2027-03-29T07:00:00.000Z'), 'lun 29 mar · 9:00', 'Monday after the March change (UTC+2)');
  eq(s('2027-10-29T07:00:00.000Z'), 'vie 29 oct · 9:00', 'Friday before the October change (UTC+2)');
  eq(s('2027-11-01T08:00:00.000Z'), 'lun 1 nov · 9:00', 'Monday after the October change (UTC+1)');
  eq(s('2026-12-12T09:00:00.000Z'), 'sáb 12 dic · 10:00', 'Saturday, accent');
  eq(s('2026-12-09T11:45:00.000Z'), 'mié 9 dic · 12:45', 'Wednesday, accent');
  eq(l(S1, NOW), 'lunes 7 de diciembre', 'same year');
  eq(l('2027-01-04T08:00:00.000Z', NOW), 'lunes 4 de enero de 2027', 'next year');
  eq(l('2026-12-12T09:00:00.000Z', NOW), 'sábado 12 de diciembre', 'sábado');
  eq(h(S1), '9:00', 'hour');
  eq(h(S2), '16:00', 'afternoon hour');
  eq(h('2026-12-07T08:45:00.000Z'), '9:45', 'minutes');
});

// === prepare: which step and which query (BK1, BK5, BK9–BK16, BK18) ===

const cmd = (data) => ({ kind: 'booking_command', data });
const bk = (data) => ({ kind: 'booking_button', data });
const P = (step, query, extra = {}) => ({ step, query, type: null, from: null, start: null, requestOnly: false, ...extra });
const PREPARE_CASES = [
  ['/cita', cmd('cita'), null, P('cita', 'agenda', { from: NOW })],
  ['/micita', cmd('micita'), null, P('micita', 'agenda', { from: NOW })],
  ['phrase, no type', { kind: 'text' }, { match: true, type: null, requestOnly: false }, P('cita', 'agenda', { from: NOW })],
  ['phrase with a type', { kind: 'text' }, { match: true, type: 'limpieza', requestOnly: false }, P('cita', 'agenda', { type: 'limpieza', from: NOW })],
  ['phrase, request only', { kind: 'text' }, { match: true, type: null, requestOnly: true }, P('cita', 'agenda', { from: NOW, requestOnly: true })],
  ['«Pedir cita» (bk:menu)', bk('bk:menu'), null, P('cita', 'agenda', { from: NOW })],
  ['type', bk('bk:t:limpieza'), null, P('slots', 'agenda', { type: 'limpieza', from: NOW })],
  ['request-only type', bk('bk:t:blanqueamiento'), null, P('request_only', 'none')],
  ['«Otro tratamiento»', bk('bk:o'), null, P('request_only', 'none')],
  ['slot → confirmation, no query', bk(`bk:s:limpieza:${code(S1)}`), null, P('confirm', 'none', { type: 'limpieza', start: S1 })],
  ['confirm → book', bk(`bk:c:limpieza:${code(S1)}`), null, P('book', 'book', { type: 'limpieza', start: S1 })],
  ['«Ver más» → after the last slot', bk(`bk:m:limpieza:${code(S3)}`), null, P('more', 'agenda', { type: 'limpieza', from: end(S3, 1) })],
  ['«Elegir otro hueco» → from now', bk('bk:r:revision'), null, P('slots', 'agenda', { type: 'revision', from: NOW })],
  ['malformed → menu, no query', bk('bk:zz'), null, P('menu', 'none')],
];
check('prepare', () => {
  const prepare = requireFn('prepare');
  const wrong = [];
  for (const [name, route, phrase, expected] of PREPARE_CASES) {
    let got;
    try { got = prepare(route, phrase, NOW); } catch (e) { got = `throws: ${e.message}`; }
    if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`  ${name}\n    expected ${JSON.stringify(expected)}\n    got      ${JSON.stringify(got)}`);
  }
  if (wrong.length) throw new Error(`${wrong.length}/${PREPARE_CASES.length} cases wrong:\n${wrong.join('\n')}`);
});
check('prepare refuses routes that are not booking steps', () => {
  const prepare = requireFn('prepare');
  let threw = false;
  try { prepare({ kind: 'start' }, null, NOW); } catch (e) { threw = true; }
  if (!threw) throw new Error('prepare() must throw for a non-booking route');
});

// === compose: text and keyboard for every result (BK9–BK20) ===

const MY = { type_code: 'limpieza', starts_at: S1, ends_at: end(S1, 45) }; // agenda_my_next (spec BK19)
const fill = (t, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, v), t);
const FECHA = { fecha: 'lunes 7 de diciembre', hora: '9:00' };
const C = (text, rows) => ({ text, rows });
const slotsView = (type, phrase, slots) => C(fill(T.SLOTS, { tipo: phrase }), SLOT_ROWS(type, slots));
const COMPOSE_CASES = [
  ['/cita, no appointment → menu', P('cita', 'agenda'), { agenda: { my_next: null, slots: null } }, C(T.TYPE_MENU, MENU_ROWS)],
  ['/cita, has one → limit (BK1)', P('cita', 'agenda'), { agenda: { my_next: MY, slots: null } },
    C(fill(T.LIMIT, { tipo: 'una limpieza', ...FECHA }), [RECEPCION])],
  ['phrase with a type → slots', P('cita', 'agenda', { type: 'limpieza' }), { agenda: { my_next: null, slots: THREE.map((s) => slot(s.iso)) } },
    slotsView('limpieza', 'una limpieza', THREE)],
  ['phrase, request only → request text', P('cita', 'agenda', { requestOnly: true }), { agenda: { my_next: null, slots: null } },
    C(T.REQUEST_ONLY, [[btn(LABELS.primeraVisita, 'bk:t:primera_visita')], RECEPCION])],
  ['/micita, has one', P('micita', 'agenda'), { agenda: { my_next: MY, slots: null } },
    C(fill(T.MY_APPOINTMENT, { tipo: 'una limpieza', ...FECHA }), [RECEPCION])],
  ['/micita, none', P('micita', 'agenda'), { agenda: { my_next: null, slots: null } },
    C(T.NO_APPOINTMENT, [[btn(LABELS.pedir, 'bk:menu')], RECEPCION])],
  ['type → 3 slots, «Ver más», reception (BK11)', P('slots', 'agenda', { type: 'limpieza' }), { agenda: { my_next: null, slots: THREE.map((s) => slot(s.iso)) } },
    slotsView('limpieza', 'una limpieza', THREE)],
  ['«Ver más» → the next slots, with its own text (R6)', P('more', 'agenda', { type: 'limpieza' }), { agenda: { my_next: null, slots: [slot(S2), slot(S3)] } },
    C(fill(T.MORE_SLOTS, { tipo: 'una limpieza' }), SLOT_ROWS('limpieza', [THREE[1], THREE[2]]))],
  ['«Ver más», nothing left → no slots', P('more', 'agenda', { type: 'limpieza' }), { agenda: { my_next: null, slots: [] } },
    C(fill(T.NO_SLOTS, { tipo: 'una limpieza' }), [RECEPCION])],
  ['«Ver más», but already has one → limit', P('more', 'agenda', { type: 'limpieza' }), { agenda: { my_next: MY, slots: [slot(S2)] } },
    C(fill(T.LIMIT, { tipo: 'una limpieza', ...FECHA }), [RECEPCION])],
  ['type → 1 slot', P('slots', 'agenda', { type: 'revision' }), { agenda: { my_next: null, slots: [slot(S2, 30)] } },
    slotsView('revision', 'una revisión', [THREE[1]])],
  ['type → no slots', P('slots', 'agenda', { type: 'primera_visita' }), { agenda: { my_next: null, slots: [] } },
    C(fill(T.NO_SLOTS, { tipo: 'una primera visita' }), [RECEPCION])],
  ['type, but already has one → limit', P('slots', 'agenda', { type: 'limpieza' }), { agenda: { my_next: MY, slots: [slot(S1)] } },
    C(fill(T.LIMIT, { tipo: 'una limpieza', ...FECHA }), [RECEPCION])],
  ['request only', P('request_only', 'none'), {}, C(T.REQUEST_ONLY, [[btn(LABELS.primeraVisita, 'bk:t:primera_visita')], RECEPCION])],
  ['malformed → menu', P('menu', 'none'), {}, C(T.TYPE_MENU, MENU_ROWS)],
  ['slot → confirmation (BK15)', P('confirm', 'none', { type: 'limpieza', start: S1 }), {},
    C(fill(T.CONFIRM, { tipo: 'una limpieza', ...FECHA }),
      [[btn(LABELS.confirmar, `bk:c:limpieza:${code(S1)}`)], [btn(LABELS.otroHueco, 'bk:r:limpieza')]])],
  ['booked', P('book', 'book', { type: 'limpieza', start: S1 }), { book: { result: 'booked', reason: null, starts_at: S1, ends_at: end(S1, 45), next_slots: null, my_next: null } },
    C(fill(T.BOOKED, { tipo: 'una limpieza', ...FECHA }), [RECEPCION])],
  ['taken → next slots', P('book', 'book', { type: 'limpieza', start: S1 }), { book: { result: 'taken', reason: null, next_slots: [slot(S2), slot(S3)], my_next: null } },
    C(T.TAKEN, SLOT_ROWS('limpieza', [THREE[1], THREE[2]]))],
  ['taken, nothing left → no slots', P('book', 'book', { type: 'limpieza', start: S1 }), { book: { result: 'taken', reason: null, next_slots: [], my_next: null } },
    C(fill(T.NO_SLOTS, { tipo: 'una limpieza' }), [RECEPCION])],
  ['invalid (too_soon) → next slots', P('book', 'book', { type: 'revision', start: S1 }), { book: { result: 'invalid', reason: 'too_soon', next_slots: [slot(S2, 30)], my_next: null } },
    C(T.UNAVAILABLE, SLOT_ROWS('revision', [THREE[1]]))],
  ['invalid (request_only) → menu', P('book', 'book', { type: 'revision', start: S1 }), { book: { result: 'invalid', reason: 'request_only', next_slots: null, my_next: null } },
    C(T.TYPE_MENU, MENU_ROWS)],
  ['limit at confirm → existing appointment (BK16, BK17)', P('book', 'book', { type: 'revision', start: S2 }), { book: { result: 'limit', reason: null, next_slots: null, my_next: MY } },
    C(fill(T.LIMIT, { tipo: 'una limpieza', ...FECHA }), [RECEPCION])],
  ['a Neon failure → D7 (BK20)', P('book', 'book', { type: 'limpieza', start: S1 }), { failed: true }, C(T.ERROR, [RECEPCION])],
  ['a Neon failure on the agenda query → D7', P('cita', 'agenda'), { failed: true }, C(T.ERROR, [RECEPCION])],
];
check('compose', () => {
  const compose = requireFn('compose');
  const wrong = [];
  for (const [name, prep, db, expected] of COMPOSE_CASES) {
    let got;
    try { got = compose(prep, db, NOW); } catch (e) { got = `throws: ${e.message}`; }
    if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`  ${name}\n    expected ${JSON.stringify(expected)}\n    got      ${JSON.stringify(got)}`);
  }
  if (wrong.length) throw new Error(`${wrong.length}/${COMPOSE_CASES.length} cases wrong:\n${wrong.join('\n')}`);
});
check('every composed callback fits in 64 bytes', () => {
  const compose = requireFn('compose');
  for (const [, prep, db] of COMPOSE_CASES) {
    for (const row of compose(prep, db, NOW).rows) for (const b of row) {
      if (Buffer.byteLength(b.data, 'utf8') > 64) throw new Error(`"${b.data}" too long`);
    }
  }
});

// === Keyboard shape for A's five fixed send nodes (R6 fix, human 2026-11-22) ===
// n8n drops a whole-keyboard expression (fixedCollection), so A sends with «Responder reserva (1)»…«(5)»:
// every booking keyboard must have 1 to 5 rows of exactly one button each.
check('every composed keyboard has 1–5 rows of exactly one button', () => {
  const compose = requireFn('compose');
  const k = requireFn('toTelegramKeyboard');
  const wrong = [];
  for (const [name, prep, db] of COMPOSE_CASES) {
    const rows = compose(prep, db, NOW).rows;
    if (rows.length < 1 || rows.length > 5) wrong.push(`${name}: ${rows.length} rows`);
    rows.forEach((row, i) => { if (row.length !== 1) wrong.push(`${name}: row ${i} has ${row.length} buttons`); });
    if (k(rows).rows.length !== rows.length) wrong.push(`${name}: toTelegramKeyboard changed the row count`);
  }
  if (wrong.length) throw new Error(wrong.join('; '));
});

// === The Telegram keyboard parameter (plan Step 5: one expression for the whole keyboard) ===

check('toTelegramKeyboard', () => {
  const k = requireFn('toTelegramKeyboard');
  eq(k([[btn('A', 'bk:menu')], [btn('B', 'handoff'), btn('C', 'bk:o')]]), { rows: [
    { row: { buttons: [{ text: 'A', additionalFields: { callback_data: 'bk:menu' } }] } },
    { row: { buttons: [{ text: 'B', additionalFields: { callback_data: 'handoff' } }, { text: 'C', additionalFields: { callback_data: 'bk:o' } }] } },
  ] }, 'rows');
  eq(k([]), { rows: [] }, 'empty');
});

// === Sync with the exported workflow A (BK23) ===

check('n8n nodes of A carry this exact code', () => {
  if (!fs.existsSync(EXPORT_PATH)) { console.log('SKIP sync check: no export of A'); return; }
  const nodes = (JSON.parse(fs.readFileSync(EXPORT_PATH, 'utf8'))[0] || {}).nodes || [];
  for (const name of NODE_NAMES) {
    const node = nodes.find((n) => n.name === name);
    if (!node) { console.log(`SKIP sync check: node "${name}" not in A's export yet`); continue; }
    if (!node.parameters.jsCode.startsWith(source)) throw new Error(`"${name}" jsCode does not start with citas.js`);
    console.log(`sync check run: "${name}" in lifecenter-telegram-demo.json`);
  }
});

// --- Report ---
console.log(`\n== SPEC-007 booking report\nphrases: ${positives.length} positives, ${negatives.length} negatives`);
if (phraseReport) {
  console.log(`  positives matched: ${positives.length - phraseReport.fn.length}/${positives.length}`);
  console.log(`  negatives matched (must be 0): ${phraseReport.fp.length}`);
  console.log(`  wrong type: ${phraseReport.wrongType.length}`);
}
console.log(`prepare cases: ${PREPARE_CASES.length} | compose cases: ${COMPOSE_CASES.length}`);
console.log(failures ? `\nRED: ${failures} check(s) failed` : '\nGREEN: all checks passed');
process.exit(failures ? 1 : 0);
