// SPEC-006 tests for n8n/code/consentimiento.js (specs/006-consent/plan.md Step 1).
// Run: node n8n/code/consentimiento.test.js   — no dependencies; exits non-zero on any failure.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_PATH = path.join(__dirname, 'consentimiento.js');
const EXPORT_PATH = path.join(ROOT, 'n8n', 'workflows', 'lifecenter-telegram-demo.json');
const NODE_NAMES = ['Clasificar', 'Decidir'];

// Spec texts (spec.md "Fixed texts"), typed here independently of the source so any drift fails.
const SPEC_NOTICE =
  'Hola, soy el asistente de LifeCenter. Para responderte: quito tu nombre, teléfono, DNI y email ' +
  'de los mensajes antes de procesarlos; envío la consulta a un modelo de IA externo (Gemini, de ' +
  'Google), y guardo el recorrido de cada consulta, sin tus datos, durante 30 días. Si me cuentas un ' +
  'síntoma te daré siempre el teléfono de la clínica. Esto es una demostración: no escribas datos ' +
  'reales. ¿Aceptas?';
const SPEC_ACCEPTED = 'Gracias. Ya puedes escribirme tu consulta.';
const SPEC_REJECTED =
  'De acuerdo, no procesaré tus consultas. Puedes llamar a recepción. Si cambias de opinión, escribe /privacidad.';
const SPEC_REVOKED =
  'He retirado tu consentimiento. No procesaré más consultas tuyas. Si cambias de opinión, escribe /privacidad.';
const SPEC_STATUS_ACCEPTED = 'Estado: aceptaste este aviso el {fecha}.';
const SPEC_STATUS_NONE = 'Estado: no has aceptado este aviso.';
const SPEC_ERROR = 'Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?'; // CHG-001 D7
const SPEC_TEXT_ONLY = 'Solo puedo leer mensajes de texto. ¿Me escribes tu consulta?'; // CHG-001 D12

// --- Load the paste-ready source the same way n8n runs it: as a plain script body. ---
// Line endings normalized to LF: a Windows checkout (core.autocrlf) must still match the node code.
const source = fs.readFileSync(SOURCE_PATH, 'utf8').replace(/\r\n/g, '\n');
const EXPORTED = ['CONSENT_TEXT_VERSION', 'CONSENT_NOTICE', 'ACCEPTED_TEXT', 'REJECTED_TEXT', 'REVOKED_TEXT',
  'STATUS_ACCEPTED', 'STATUS_NONE', 'ERROR_TEXT', 'TEXT_ONLY_TEXT', 'BUTTON_LABELS', 'CALLBACK_HANDOFF',
  'CALLBACK_WITHDRAW', 'callbackAccept', 'callbackReject', 'parseCommand', 'parseCallback', 'classifyUpdate',
  'isConsentInForce', 'formatDate', 'decide'];
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
  if (typeof M[name] !== 'function') throw new Error(`${name} is not implemented in consentimiento.js`);
  return M[name];
}

const V = '1';
const OLD = '0';

// --- Constants and fixed texts (spec "Fixed texts", C7, C22) ---
check('text version', () => eq(M.CONSENT_TEXT_VERSION, V, 'CONSENT_TEXT_VERSION'));
check('fixed texts', () => {
  eq(M.CONSENT_NOTICE, SPEC_NOTICE, 'CONSENT_NOTICE');
  eq(M.ACCEPTED_TEXT, SPEC_ACCEPTED, 'ACCEPTED_TEXT');
  eq(M.REJECTED_TEXT, SPEC_REJECTED, 'REJECTED_TEXT');
  eq(M.REVOKED_TEXT, SPEC_REVOKED, 'REVOKED_TEXT');
  eq(M.STATUS_ACCEPTED, SPEC_STATUS_ACCEPTED, 'STATUS_ACCEPTED');
  eq(M.STATUS_NONE, SPEC_STATUS_NONE, 'STATUS_NONE');
  eq(M.ERROR_TEXT, SPEC_ERROR, 'ERROR_TEXT');
  eq(M.TEXT_ONLY_TEXT, SPEC_TEXT_ONLY, 'TEXT_ONLY_TEXT');
});
check('button labels', () => eq(M.BUTTON_LABELS,
  { handoff: 'Hablar con recepción', accept: 'Acepto', reject: 'No acepto', withdraw: 'Retirar consentimiento' },
  'BUTTON_LABELS'));
check('callback_data values', () => {
  eq(M.CALLBACK_HANDOFF, 'handoff', 'CALLBACK_HANDOFF');
  eq(M.CALLBACK_WITHDRAW, 'consent:withdraw', 'CALLBACK_WITHDRAW');
  eq(requireFn('callbackAccept')(), `consent:accept:${V}`, 'callbackAccept()');
  eq(requireFn('callbackReject')(), `consent:reject:${V}`, 'callbackReject()');
});
check('callback_data fits in 64 bytes (C7)', () => {
  const all = [M.CALLBACK_HANDOFF, M.CALLBACK_WITHDRAW, requireFn('callbackAccept')(), requireFn('callbackReject')()];
  for (const d of all) {
    const n = Buffer.byteLength(String(d), 'utf8');
    if (n < 1 || n > 64) throw new Error(`"${d}" is ${n} bytes`);
  }
});

// --- Commands (C14–C16, spec "Command") ---
check('parseCommand', () => {
  const p = requireFn('parseCommand');
  eq(p('/start'), 'start', '/start');
  eq(p('/privacidad'), 'privacidad', '/privacidad');
  eq(p('  /privacidad  '), 'privacidad', 'surrounding spaces');
  eq(p('/start@LifeCenterBot'), 'start', '/start@bot');
  eq(p('/privacidad@LifeCenter_bot'), 'privacidad', '/privacidad@bot');
  eq(p('/start hola'), null, 'extra text');
  eq(p('quiero ver /privacidad'), null, 'command inside a sentence');
  // Case-insensitive (human, 2026-11-22): phone keyboards often capitalize the first letter.
  eq(p('/Privacidad'), 'privacidad', 'capitalized by the keyboard');
  eq(p('/PRIVACIDAD'), 'privacidad', 'upper case');
  eq(p('/Start'), 'start', '/Start');
  eq(p('/START@LifeCenterBot'), 'start', 'upper case with @bot');
  eq(p('/pRiVaCiDaD'), 'privacidad', 'mixed case');
  eq(p('/Privacidad por favor'), null, 'capitalized, with extra text');
  eq(p('/ayuda'), null, 'other command');
  eq(p(''), null, 'empty');
});

// --- Buttons (C7–C13) ---
check('parseCallback', () => {
  const p = requireFn('parseCallback');
  eq(p('handoff'), { kind: 'handoff', version: null }, 'handoff');
  eq(p(`consent:accept:${V}`), { kind: 'accept', version: V }, 'accept');
  eq(p(`consent:reject:${OLD}`), { kind: 'reject', version: OLD }, 'reject old');
  eq(p('consent:withdraw'), { kind: 'withdraw', version: null }, 'withdraw');
  eq(p('consent:accept:'), { kind: 'unknown_button', version: null }, 'accept without version');
  eq(p('otra cosa'), { kind: 'unknown_button', version: null }, 'garbage');
  eq(p(undefined), { kind: 'unknown_button', version: null }, 'missing');
});

// --- Update classification (synthetic Telegram updates, fake ids 900001…) ---
const msg = (text, extra = {}) => ({
  update_id: 1, message: { message_id: 10, from: { id: 900001, first_name: 'Prueba' }, chat: { id: 900001, type: 'private' }, date: 0, ...(text === undefined ? {} : { text }), ...extra },
});
const cb = (data) => ({
  update_id: 2, callback_query: { id: 'cbq-1', from: { id: 900002 }, data, message: { message_id: 11, chat: { id: 900002 } } },
});
check('classifyUpdate', () => {
  const c = requireFn('classifyUpdate');
  eq(c(msg('¿Cuánto cuesta una limpieza?')), { kind: 'text', fromId: '900001', chatId: 900001, callbackQueryId: null, version: null }, 'text');
  eq(c(msg('/start')).kind, 'start', '/start');
  eq(c(msg('/privacidad@LifeCenterBot')).kind, 'privacidad', '/privacidad@bot');
  eq(c(msg('/Privacidad')).kind, 'privacidad', '/Privacidad');
  eq(c(msg(undefined, { sticker: { file_id: 'x' } })), { kind: 'other', fromId: '900001', chatId: 900001, callbackQueryId: null, version: null }, 'sticker');
  eq(c(msg('')).kind, 'other', 'empty text counts as no text (D12)');
  eq(c(cb('handoff')), { kind: 'handoff', fromId: '900002', chatId: 900002, callbackQueryId: 'cbq-1', version: null }, 'handoff');
  eq(c(cb(`consent:accept:${V}`)), { kind: 'accept', fromId: '900002', chatId: 900002, callbackQueryId: 'cbq-1', version: V }, 'accept');
  eq(c(cb(`consent:reject:${V}`)).kind, 'reject', 'reject');
  eq(c(cb('consent:withdraw')).kind, 'withdraw', 'withdraw');
  eq(c(cb('zzz')).kind, 'unknown_button', 'unknown');
});

// --- Consent in force and dates (C22) ---
const accepted = (version = V, decided_at = '2026-11-21T10:00:00.000Z') => ({ status: 'accepted', text_version: version, decided_at });
check('isConsentInForce', () => {
  const f = requireFn('isConsentInForce');
  eq(f(accepted()), true, 'accepted, current version');
  eq(f(accepted(OLD)), false, 'accepted, older version');
  eq(f({ status: 'revoked', text_version: V, decided_at: '2026-11-21T10:00:00Z' }), false, 'revoked');
  eq(f({}), false, 'no row (empty item from "Always output data")');
  eq(f(null), false, 'null');
  eq(f(undefined), false, 'undefined');
});
check('formatDate in Europe/Madrid', () => {
  const f = requireFn('formatDate');
  eq(f('2026-07-31T22:30:00Z'), '01/08/2026', 'summer (UTC+2)');
  eq(f('2026-12-31T23:30:00Z'), '01/01/2027', 'winter (UTC+1)');
  eq(f(new Date('2026-11-21T10:00:00Z')), '21/11/2026', 'Date object');
});

// --- Decision table (plan Step 1; C2–C16) ---
const route = (kind, version = null) => ({ kind, fromId: '900001', chatId: 900001, callbackQueryId: null, version });
const URGENT = { text: 'TEXTO DE URGENCIA', handoff: true, reason: 'urgency', urgency_level: 'urgent', matched: ['x'] };
const SEVERE = { text: 'TEXTO GRAVE', handoff: true, reason: 'urgency', urgency_level: 'severe', matched: ['y'] };
const NONE = { question: 'pregunta', urgency_level: 'none' };
const reply = (text, keyboard) => ({ action: 'reply', text, keyboard });
const NOTICE = reply(SPEC_NOTICE, 'consent');
const STATUS_OK = reply(`${SPEC_NOTICE}\n\n${SPEC_STATUS_ACCEPTED.replace('{fecha}', '21/11/2026')}`, 'withdraw');
const STATUS_NO = reply(`${SPEC_NOTICE}\n\n${SPEC_STATUS_NONE}`, 'consent');
const ERROR = reply(SPEC_ERROR, 'handoff');
const CORE = { action: 'core', text: null, keyboard: null };

const CASES = [
  // [name, input, expected]
  ['text, urgent, no consent → urgency reply (C2)', { route: route('text'), urgency: URGENT, consent: {} }, reply('TEXTO DE URGENCIA', 'handoff')],
  ['text, severe, revoked → urgency reply (C2)', { route: route('text'), urgency: SEVERE, consent: { status: 'revoked', text_version: V } }, reply('TEXTO GRAVE', 'handoff')],
  ['text, urgent, older version → urgency reply (C2, C22)', { route: route('text'), urgency: URGENT, consent: accepted(OLD) }, reply('TEXTO DE URGENCIA', 'handoff')],
  ['text, urgent, lookup failed → urgency reply (C6)', { route: route('text'), urgency: URGENT, consent: null, lookupFailed: true }, reply('TEXTO DE URGENCIA', 'handoff')],
  ['text, urgent, in force → core (C3)', { route: route('text'), urgency: URGENT, consent: accepted() }, CORE],
  ['text, none, in force → core (C3)', { route: route('text'), urgency: NONE, consent: accepted() }, CORE],
  ['text, none, lookup failed → error (C6)', { route: route('text'), urgency: NONE, consent: null, lookupFailed: true }, ERROR],
  ['text, none, no consent → notice (C4)', { route: route('text'), urgency: NONE, consent: {} }, NOTICE],
  ['text, none, older version → notice (C4, C22)', { route: route('text'), urgency: NONE, consent: accepted(OLD) }, NOTICE],
  ['text, no urgency output → treated as none', { route: route('text'), urgency: null, consent: {} }, NOTICE],
  ['other, in force → D12 (C5)', { route: route('other'), urgency: null, consent: accepted() }, reply(SPEC_TEXT_ONLY, 'none')],
  ['other, no consent → notice (C5)', { route: route('other'), urgency: null, consent: {} }, NOTICE],
  ['other, lookup failed → error (C6)', { route: route('other'), urgency: null, consent: null, lookupFailed: true }, ERROR],
  ['/start, no consent → notice (C14)', { route: route('start'), urgency: null, consent: {} }, NOTICE],
  ['/start, in force → status accepted (C15)', { route: route('start'), urgency: null, consent: accepted() }, STATUS_OK],
  ['/privacidad, in force → status accepted (C15)', { route: route('privacidad'), urgency: null, consent: accepted() }, STATUS_OK],
  ['/privacidad, no consent → status none (C15)', { route: route('privacidad'), urgency: null, consent: {} }, STATUS_NO],
  ['/privacidad, older version → status none (C15, C22)', { route: route('privacidad'), urgency: null, consent: accepted(OLD) }, STATUS_NO],
  ['/privacidad, lookup failed → error (C6)', { route: route('privacidad'), urgency: null, consent: null, lookupFailed: true }, ERROR],
  ['accept, current version → accept (C8)', { route: route('accept', V), urgency: null, consent: {} }, { action: 'accept', text: SPEC_ACCEPTED, keyboard: 'none' }],
  ['accept, current version, already accepted → accept again (C8)', { route: route('accept', V), urgency: null, consent: accepted() }, { action: 'accept', text: SPEC_ACCEPTED, keyboard: 'none' }],
  ['accept, older version → notice, no write (C11)', { route: route('accept', OLD), urgency: null, consent: {} }, NOTICE],
  ['reject, current version → rejected, no write (C9)', { route: route('reject', V), urgency: null, consent: {} }, reply(SPEC_REJECTED, 'none')],
  ['reject, older version → notice (C11)', { route: route('reject', OLD), urgency: null, consent: {} }, NOTICE],
  ['unknown button → notice (C11)', { route: route('unknown_button'), urgency: null, consent: {} }, NOTICE],
  ['withdraw → withdraw (C10)', { route: route('withdraw'), urgency: null, consent: accepted() }, { action: 'withdraw', text: SPEC_REVOKED, keyboard: 'none' }],
  ['withdraw, lookup failed → error (C6)', { route: route('withdraw'), urgency: null, consent: null, lookupFailed: true }, ERROR],
  ['accept, lookup failed → error (C6)', { route: route('accept', V), urgency: null, consent: null, lookupFailed: true }, ERROR],
];
check('decide: decision table', () => {
  const decide = requireFn('decide');
  const wrong = [];
  for (const [name, input, expected] of CASES) {
    let got;
    try { got = decide(input); } catch (e) { got = `throws: ${e.message}`; }
    if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`  ${name}\n    expected ${JSON.stringify(expected)}\n    got      ${JSON.stringify(got)}`);
  }
  if (wrong.length) throw new Error(`${wrong.length}/${CASES.length} cases wrong:\n${wrong.join('\n')}`);
});
check('decide: handoff never reaches decide (C12)', () => {
  const decide = requireFn('decide');
  let threw = false;
  try { decide({ route: route('handoff'), urgency: null, consent: {} }); } catch (e) { threw = true; }
  if (!threw) throw new Error('decide() must throw for the handoff route: it has its own branch');
});
check('decide: urgency reply never carries the notice (C2)', () => {
  const r = requireFn('decide')({ route: route('text'), urgency: URGENT, consent: {} });
  if (String(r.text).includes(SPEC_NOTICE)) throw new Error('urgency reply contains the consent notice');
});

// --- SPEC-007 booking routes (plan Step 1; BK1, BK8, BK18) ---
// /cita and /micita are booking commands; any bk:… button is a booking button. Non-booking routes
// keep their SPEC-006 shape; booking routes add `data` (the command, or the raw callback_data).
check('SPEC-007: parseCommand recognizes /cita and /micita in any case', () => {
  const p = requireFn('parseCommand');
  eq(p('/cita'), 'cita', '/cita');
  eq(p('/Cita'), 'cita', '/Cita');
  eq(p('  /MICITA@LifeCenterBot '), 'micita', '/MICITA@bot');
  eq(p('/cita para mañana'), null, 'extra text');
  eq(p('/citas'), null, 'other command');
});
check('SPEC-007: parseCallback classifies bk: buttons', () => {
  const p = requireFn('parseCallback');
  eq(p('bk:menu'), { kind: 'booking_button', version: null }, 'bk:menu');
  eq(p('bk:c:limpieza:abcde'), { kind: 'booking_button', version: null }, 'bk:c');
  eq(p('bk'), { kind: 'unknown_button', version: null }, 'no colon');
});
check('SPEC-007: classifyUpdate builds booking routes with data', () => {
  const c = requireFn('classifyUpdate');
  eq(c(msg('/cita')), { kind: 'booking_command', fromId: '900001', chatId: 900001, callbackQueryId: null, version: null, data: 'cita' }, '/cita');
  eq(c(msg('/MiCita')), { kind: 'booking_command', fromId: '900001', chatId: 900001, callbackQueryId: null, version: null, data: 'micita' }, '/MiCita');
  eq(c(cb('bk:t:limpieza')), { kind: 'booking_button', fromId: '900002', chatId: 900002, callbackQueryId: 'cbq-1', version: null, data: 'bk:t:limpieza' }, 'bk:t');
  eq(c(msg('/start')).kind, 'start', '/start unchanged');
  eq(c(cb('handoff')).kind, 'handoff', 'handoff unchanged');
});
const BOOKING_CASES = [
  ['/cita, in force → booking', { route: { ...route('booking_command'), data: 'cita' }, urgency: null, consent: accepted() }, { action: 'booking', text: null, keyboard: null }],
  ['/micita, in force → booking', { route: { ...route('booking_command'), data: 'micita' }, urgency: null, consent: accepted() }, { action: 'booking', text: null, keyboard: null }],
  ['bk: button, in force → booking', { route: { ...route('booking_button'), data: 'bk:menu' }, urgency: null, consent: accepted() }, { action: 'booking', text: null, keyboard: null }],
  ['/cita, no consent → notice (BK8)', { route: { ...route('booking_command'), data: 'cita' }, urgency: null, consent: {} }, NOTICE],
  ['bk: button, revoked → notice (BK8)', { route: { ...route('booking_button'), data: 'bk:menu' }, urgency: null, consent: { status: 'revoked', text_version: V } }, NOTICE],
  ['/micita, older version → notice (BK8)', { route: { ...route('booking_command'), data: 'micita' }, urgency: null, consent: accepted(OLD) }, NOTICE],
  ['bk: button, lookup failed → D7', { route: { ...route('booking_button'), data: 'bk:menu' }, urgency: null, consent: null, lookupFailed: true }, ERROR],
  ['text, in force → core (the phrase check comes after, in A)', { route: route('text'), urgency: NONE, consent: accepted() }, CORE],
];
check('SPEC-007: decide routes booking steps', () => {
  const decide = requireFn('decide');
  const wrong = [];
  for (const [name, input, expected] of BOOKING_CASES) {
    let got;
    try { got = decide(input); } catch (e) { got = `throws: ${e.message}`; }
    if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`  ${name}\n    expected ${JSON.stringify(expected)}\n    got      ${JSON.stringify(got)}`);
  }
  if (wrong.length) throw new Error(`${wrong.length}/${BOOKING_CASES.length} cases wrong:\n${wrong.join('\n')}`);
});

// --- Urgencies without consent, end to end with the real detector (C2; human, 2026-11-22) ---
// Runs urgencias.js with B's node wiring on real messages, then decide(): a person who has not
// accepted yet, or who withdrew, always gets the urgency reply (with the 112 when severe), never
// the notice, and B is not called.
const urgSource = fs.readFileSync(path.join(__dirname, 'urgencias.js'), 'utf8').replace(/\r\n/g, '\n');
const U = new Function(urgSource + '\nreturn { detectUrgency, composeUrgencyReply };')();
const wiredUrgency = (question) => { // B's "Detectar urgencia" wiring, also used in A (plan Step 4)
  const r = U.detectUrgency(question);
  if (r.level === 'none') return { question, urgency_level: 'none' };
  return { text: U.composeUrgencyReply(r.level), handoff: true, reason: 'urgency', urgency_level: r.level, matched: r.matched };
};
const NO_CONSENT_STATES = [
  ['never accepted (no row)', {}],
  ['withdrawn', { status: 'revoked', text_version: V, decided_at: '2026-11-20T10:00:00Z' }],
  ['accepted an older notice', accepted(OLD)],
];
const URGENCY_MESSAGES = [
  ['urgent', 'me sangra mucho la encia desde ayer'],
  ['severe', 'se me ha hinchado la cara y me cuesta tragar'],
];
check('urgency without consent: real detector → urgency reply, never B (C2)', () => {
  const decide = requireFn('decide');
  const wrong = [];
  for (const [level, text] of URGENCY_MESSAGES) {
    const urgency = wiredUrgency(text);
    if (urgency.urgency_level !== level) { wrong.push(`detector gave ${urgency.urgency_level} for "${text}"`); continue; }
    for (const [state, consent] of NO_CONSENT_STATES) {
      const got = decide({ route: route('text'), urgency, consent });
      const expected = reply(U.composeUrgencyReply(level), 'handoff');
      if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`${level}, ${state}: got ${JSON.stringify(got)}`);
      if (level === 'severe' && !String(got.text).includes('112')) wrong.push(`severe, ${state}: no 112`);
      if (got.action === 'core') wrong.push(`${level}, ${state}: B would be called`);
    }
  }
  if (wrong.length) throw new Error(wrong.join('; '));
});

// --- Sync with the exported workflow A (C23, C25) ---
check('n8n nodes of A carry this exact code', () => {
  if (!fs.existsSync(EXPORT_PATH)) { console.log('SKIP sync check: no export of A'); return; }
  const wf = JSON.parse(fs.readFileSync(EXPORT_PATH, 'utf8'));
  const nodes = (Array.isArray(wf) ? wf[0] : wf).nodes;
  // SPEC-007: this module gained the booking routes in R1, and A's export gets them in R5. Until A
  // has the booking nodes, the export still carries the SPEC-006 module, so the check waits.
  if (!nodes.some((n) => n.name === 'Preparar reserva')) {
    console.log("SKIP sync check: A's export has no booking nodes yet; consentimiento.js is checked against it from SPEC-007 R5 (hasta R5)");
    return;
  }
  for (const name of NODE_NAMES) {
    const node = nodes.find((n) => n.name === name);
    if (!node) { console.log(`SKIP sync check: node "${name}" not in A's export yet`); continue; }
    if (!node.parameters.jsCode.startsWith(source)) throw new Error(`"${name}" jsCode does not start with consentimiento.js`);
    console.log(`sync check run: "${name}" in lifecenter-telegram-demo.json`);
  }
});

console.log(`\n== SPEC-006 consent report\ndecision cases: ${CASES.length}`);
console.log(failures ? `\nRED: ${failures} check(s) failed` : '\nGREEN: all checks passed');
process.exit(failures ? 1 : 0);
