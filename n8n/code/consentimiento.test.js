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
  'isConsentInForce', 'formatDate', 'decide', 'HANDOFF_NO_CONSENT_TEXT', 'COMPLAINT_NO_CONSENT_TEXT', 'detectComplaintPhrase'];
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
  eq(p('handoff'), { kind: 'handoff', version: null, reason: 'p' }, 'handoff'); // SPEC-010 RH2: a request
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
  // SPEC-010 RH2: the handoff button carries its reason; the old `handoff` reads as `p` (request).
  eq(c(cb('handoff')), { kind: 'handoff', fromId: '900002', chatId: 900002, callbackQueryId: 'cbq-1', version: null, reason: 'p' }, 'handoff');
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
// SPEC-010 RH1, RH7: the handoff button now goes through decide (consent check); C12's own branch is gone.
check('decide: a group update never reaches decide (SPEC-010 RH12)', () => {
  const decide = requireFn('decide');
  let threw = false;
  try { decide({ route: { kind: 'group' }, urgency: null, consent: {} }); } catch (e) { threw = true; }
  if (!threw) throw new Error('decide() must throw for a group update: it has its own branch');
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
// SPEC-008 MC10: the booking action now says whether consent is in force (consent: true | false).
const BOOKING = { action: 'booking', text: null, keyboard: null, consent: true };
const BOOKING_NO_CONSENT = { action: 'booking', text: null, keyboard: null, consent: false };
const BOOKING_CASES = [
  ['/cita, in force → booking', { route: { ...route('booking_command'), data: 'cita' }, urgency: null, consent: accepted() }, BOOKING],
  ['/micita, in force → booking', { route: { ...route('booking_command'), data: 'micita' }, urgency: null, consent: accepted() }, BOOKING],
  ['bk: button, in force → booking', { route: { ...route('booking_button'), data: 'bk:menu' }, urgency: null, consent: accepted() }, BOOKING],
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

// --- SPEC-008 MC10 (Q8, extended at the spec review, human 2026-11-23) ---
// Without consent, only «Anular» (bk:a:<start>), «Sí, anular» (bk:ac:<start>) and the «Mantener mi
// cita» of the cancel confirmation (bk:v:<start>) go through, flagged consent: false. Every other
// booking step still gets the notice, and a failed lookup still gives D7.
const btnRoute = (data) => ({ ...route('booking_button'), data });
const REVOKED_ROW = { status: 'revoked', text_version: V, decided_at: '2026-11-23T10:00:00Z' };
const CHANGE_CASES = [
  ['bk:a, no consent → booking, consent false', { route: btnRoute('bk:a:abcde'), urgency: null, consent: {} }, BOOKING_NO_CONSENT],
  ['bk:ac, revoked → booking, consent false', { route: btnRoute('bk:ac:abcde'), urgency: null, consent: REVOKED_ROW }, BOOKING_NO_CONSENT],
  ['bk:v:<start>, older version → booking, consent false', { route: btnRoute('bk:v:abcde'), urgency: null, consent: accepted(OLD) }, BOOKING_NO_CONSENT],
  ['bk:a, in force → booking, consent true', { route: btnRoute('bk:a:abcde'), urgency: null, consent: accepted() }, BOOKING],
  ['bk:v without a start, revoked → notice', { route: btnRoute('bk:v'), urgency: null, consent: REVOKED_ROW }, NOTICE],
  ['bk:x («Cambiar»), revoked → notice', { route: btnRoute('bk:x:abcde'), urgency: null, consent: REVOKED_ROW }, NOTICE],
  ['bk:xc («Confirmar cambio»), revoked → notice', { route: btnRoute('bk:xc:abcde:fghij'), urgency: null, consent: REVOKED_ROW }, NOTICE],
  ['bk:xs, no consent → notice', { route: btnRoute('bk:xs:abcde:fghij'), urgency: null, consent: {} }, NOTICE],
  ['bk:menu, revoked → notice', { route: btnRoute('bk:menu'), urgency: null, consent: REVOKED_ROW }, NOTICE],
  ['bk:a malformed, no consent → notice', { route: btnRoute('bk:a:@@'), urgency: null, consent: {} }, NOTICE],
  ['bk:a with two codes, no consent → notice', { route: btnRoute('bk:a:abcde:fghij'), urgency: null, consent: {} }, NOTICE],
  ['bk:ac, lookup failed → D7', { route: btnRoute('bk:ac:abcde'), urgency: null, consent: null, lookupFailed: true }, ERROR],
  ['/micita, revoked → notice', { route: { ...route('booking_command'), data: 'micita' }, urgency: null, consent: REVOKED_ROW }, NOTICE],
  // SPEC-009 RM6: the reminder buttons need consent in force, like every booking step but cancelling.
  ['bk:ry (recordármela), in force → booking', { route: btnRoute('bk:ry:abcde'), urgency: null, consent: accepted() }, BOOKING],
  ['bk:i («Iré»), in force → booking', { route: btnRoute('bk:i:abcde'), urgency: null, consent: accepted() }, BOOKING],
  ['bk:ry, no consent → notice', { route: btnRoute('bk:ry:abcde'), urgency: null, consent: {} }, NOTICE],
  ['bk:rn, revoked → notice', { route: btnRoute('bk:rn:abcde'), urgency: null, consent: REVOKED_ROW }, NOTICE],
  ['bk:rq, older version → notice', { route: btnRoute('bk:rq:abcde'), urgency: null, consent: accepted(OLD) }, NOTICE],
  ['bk:i («Iré»), revoked → notice', { route: btnRoute('bk:i:abcde'), urgency: null, consent: REVOKED_ROW }, NOTICE],
  ['bk:i, lookup failed → D7', { route: btnRoute('bk:i:abcde'), urgency: null, consent: null, lookupFailed: true }, ERROR],
];
check('SPEC-008: decide lets only the cancel buttons through without consent', () => {
  const decide = requireFn('decide');
  const wrong = [];
  for (const [name, input, expected] of CHANGE_CASES) {
    let got;
    try { got = decide(input); } catch (e) { got = `throws: ${e.message}`; }
    if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`  ${name}\n    expected ${JSON.stringify(expected)}\n    got      ${JSON.stringify(got)}`);
  }
  if (wrong.length) throw new Error(`${wrong.length}/${CHANGE_CASES.length} cases wrong:\n${wrong.join('\n')}`);
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

// --- SPEC-010: reception handoff, complaints, ratings and group updates (RH1–RH18) ---
const SPEC_HANDOFF_NO_CONSENT = 'Ahora mismo no puedo pasar tu consulta automáticamente. Llama a recepción en horario de atención.'; // D8
const SPEC_COMPLAINT_NO_CONSENT = 'Para pasar tu queja a recepción necesito tu consentimiento (/privacidad). También puedes llamar a recepción en horario de atención.';
const COMPLAINT_DATASET_PATH = path.join(ROOT, 'evals', 'complaint_phrases.yaml');
function readPhrases(file) {
  const items = [];
  fs.readFileSync(file, 'utf8').split(/\r?\n/).forEach((line, i) => {
    if (/^\s*(#.*)?$/.test(line)) return;
    let m;
    if ((m = /^- text: "((?:[^"\\]|\\.)*)"$/.exec(line))) items.push({ text: m[1] });
    else if ((m = /^ {2}expected: (complaint|booking|change|none)$/.exec(line)) && items.length) items[items.length - 1].expected = m[1];
    else if (/^ {2}type: /.test(line)) { /* booking dataset field */ } else throw new Error(`${path.basename(file)}:${i + 1}: unexpected line: ${line}`);
  });
  return items;
}
const complaintSet = readPhrases(COMPLAINT_DATASET_PATH);
const complaintPositives = complaintSet.filter((d) => d.expected === 'complaint');
const complaintNegatives = complaintSet.filter((d) => d.expected === 'none');

check('SPEC-010: fixed texts', () => {
  eq(M.HANDOFF_NO_CONSENT_TEXT, SPEC_HANDOFF_NO_CONSENT, 'HANDOFF_NO_CONSENT_TEXT');
  eq(M.COMPLAINT_NO_CONSENT_TEXT, SPEC_COMPLAINT_NO_CONSENT, 'COMPLAINT_NO_CONSENT_TEXT');
});
check('SPEC-010: /queja is a command, in any case', () => {
  const p = requireFn('parseCommand');
  eq(p('/queja'), 'queja', '/queja');
  eq(p('/Queja@LifeCenterBot'), 'queja', '/Queja@bot');
  eq(p('/quejas'), null, '/quejas');
  eq(requireFn('classifyUpdate')(msg('/queja')).kind, 'complaint_command', 'route kind');
});
check('SPEC-010: parseCallback — handoff:a/u/p/q, hs, hn, rt', () => {
  const p = requireFn('parseCallback');
  eq(p('handoff'), { kind: 'handoff', version: null, reason: 'p' }, 'old handoff');
  for (const r of ['a', 'u', 'p', 'q']) eq(p(`handoff:${r}`), { kind: 'handoff', version: null, reason: r }, `handoff:${r}`);
  for (const r of ['a', 'u', 'p', 'q']) eq(p(`hs:${r}`), { kind: 'handoff_confirm', version: null, reason: r }, `hs:${r}`);
  eq(p('hn'), { kind: 'handoff_cancel', version: null }, 'hn');
  eq(p('rt:u'), { kind: 'rating', version: null, value: 'up' }, 'rt:u');
  eq(p('rt:d'), { kind: 'rating', version: null, value: 'down' }, 'rt:d');
  for (const bad of ['handoff:x', 'handoff:', 'hs:', 'hs:z', 'rt:x', 'rt:', 'hn:1']) eq(p(bad).kind, 'unknown_button', bad);
});
const gmsg = (o) => ({ update_id: 3, message: { message_id: 50, from: { id: 777001, first_name: 'Recepción' }, chat: { id: -1001234567890, type: 'supergroup', title: 'LifeCenter Recepción' }, date: 0, text: 'hola', ...o } });
check('SPEC-010: classifyUpdate — any non-private chat is a group update, with no sender id (RH12, A3)', () => {
  const c = requireFn('classifyUpdate');
  eq(c(gmsg({})), { kind: 'group', chatId: '-1001234567890', messageId: 50, replyToMessageId: null, replyToBot: false, text: 'hola', callbackData: null, callbackQueryId: null }, 'a staff message');
  eq(c(gmsg({ text: 'Sí, aceptamos Sanitas.', reply_to_message: { message_id: 41, from: { id: 5, is_bot: true } } })),
    { kind: 'group', chatId: '-1001234567890', messageId: 50, replyToMessageId: 41, replyToBot: true, text: 'Sí, aceptamos Sanitas.', callbackData: null, callbackQueryId: null }, 'a reply to the bot');
  eq(c(gmsg({ text: undefined, sticker: { file_id: 'x' }, reply_to_message: { message_id: 41, from: { id: 5, is_bot: true } } })).text, null, 'a sticker as reply');
  eq(c(gmsg({ text: '/start' })).kind, 'group', 'a command in a group is a group update');
  eq(c(gmsg({ text: 'Acepto', chat: { id: -400, type: 'group' } })).kind, 'group', 'a basic group');
  eq(c({ update_id: 4, callback_query: { id: 'cq-9', from: { id: 777001 }, data: 'hc:R-7KQ3', message: { message_id: 52, chat: { id: -1001234567890, type: 'supergroup' } } } }),
    { kind: 'group', chatId: '-1001234567890', messageId: 52, replyToMessageId: null, replyToBot: false, text: null, callbackData: 'hc:R-7KQ3', callbackQueryId: 'cq-9' }, '«Cerrar»');
  const g = c(gmsg({}));
  if ('fromId' in g) throw new Error('a group update must not carry the sender id');
  eq(c(msg('hola')).kind, 'text', 'a private chat is unchanged');
});

check('SPEC-010: the complaint dataset', () => {
  if (complaintPositives.length < 15 || complaintNegatives.length < 15) throw new Error(`${complaintPositives.length} positives, ${complaintNegatives.length} negatives`);
});
check('SPEC-010: detectComplaintPhrase over its dataset (every positive, 0 negatives)', () => {
  const d = requireFn('detectComplaintPhrase');
  const fn = complaintPositives.filter((x) => !d(x.text));
  const fp = complaintNegatives.filter((x) => d(x.text));
  const msgs = [];
  if (fn.length) msgs.push(`missed: ${fn.map((x) => x.text).join(' | ')}`);
  if (fp.length) msgs.push(`false positives: ${fp.map((x) => x.text).join(' | ')}`);
  if (msgs.length) throw new Error(msgs.join('; '));
});
check('SPEC-010: the complaint detector never matches the booking or change datasets', () => {
  const d = requireFn('detectComplaintPhrase');
  const others = [...readPhrases(path.join(ROOT, 'evals', 'booking_phrases.yaml')), ...readPhrases(path.join(ROOT, 'evals', 'change_phrases.yaml'))];
  const hit = others.filter((x) => d(x.text));
  if (hit.length) throw new Error(hit.map((x) => x.text).join(' | '));
});

const H = (step, reason, extra = {}) => ({ action: 'handoff', text: null, keyboard: null, step, reason, ...extra });
const r10 = (kind, extra = {}) => ({ kind, fromId: '900010', chatId: 900010, callbackQueryId: 'cq', version: null, ...extra });
const HANDOFF_CASES = [
  ['«Hablar con recepción» with consent → ask, with its reason (RH1, RH2)', { route: r10('handoff', { reason: 'a' }), urgency: null, consent: accepted() }, H('ask', 'a')],
  ['old «Hablar con recepción» → ask, request', { route: r10('handoff', { reason: 'p' }), urgency: null, consent: accepted() }, H('ask', 'p')],
  ['«Hablar con recepción» without consent → the D8 text, nothing stored (RH7)', { route: r10('handoff', { reason: 'u' }), urgency: null, consent: {} }, { action: 'reply', text: SPEC_HANDOFF_NO_CONSENT, keyboard: 'none' }],
  ['«Hablar con recepción», lookup failed → the D8 text', { route: r10('handoff', { reason: 'a' }), urgency: null, consent: null, lookupFailed: true }, { action: 'reply', text: SPEC_HANDOFF_NO_CONSENT, keyboard: 'none' }],
  ['«Sí, pasar a recepción» with consent → confirm (RH3)', { route: r10('handoff_confirm', { reason: 'q' }), urgency: null, consent: accepted() }, H('confirm', 'q')],
  ['«Sí, pasar a recepción» without consent → the D8 text', { route: r10('handoff_confirm', { reason: 'a' }), urgency: null, consent: {} }, { action: 'reply', text: SPEC_HANDOFF_NO_CONSENT, keyboard: 'none' }],
  ['«No» → cancel, with or without consent (RH6)', { route: r10('handoff_cancel'), urgency: null, consent: {} }, H('cancel', null)],
  ['/queja with consent → ask, complaint (RH13)', { route: r10('complaint_command', { callbackQueryId: null, data: 'queja' }), urgency: null, consent: accepted() }, H('ask', 'q')],
  ['/queja without consent → the complaint no-consent text (RH15)', { route: r10('complaint_command', { callbackQueryId: null, data: 'queja' }), urgency: null, consent: {} }, { action: 'reply', text: SPEC_COMPLAINT_NO_CONSENT, keyboard: 'none' }],
  ['a complaint phrase with consent → ask, complaint (RH13)', { route: r10('text', { callbackQueryId: null }), urgency: NONE, consent: accepted(), question: 'quiero poner una queja por el trato recibido' }, H('ask', 'q')],
  ['a complaint phrase without consent → the complaint no-consent text (RH15)', { route: r10('text', { callbackQueryId: null }), urgency: NONE, consent: {}, question: 'quiero hacer una reclamación' }, { action: 'reply', text: SPEC_COMPLAINT_NO_CONSENT, keyboard: 'none' }],
  ['a complaint phrase with an urgency, with consent → B, the urgency wins (RH14)', { route: r10('text', { callbackQueryId: null }), urgency: URGENT, consent: accepted(), question: 'quiero poner una queja, me sangra mucho la encía' }, { action: 'core', text: null, keyboard: null }],
  ['a complaint phrase with an urgency, without consent → the urgency reply', { route: r10('text', { callbackQueryId: null }), urgency: URGENT, consent: {}, question: 'quiero poner una queja, me sangra mucho la encía' }, { action: 'reply', text: URGENT.text, keyboard: 'handoff' }],
  ['a text while a handoff waits for it → text (RH4)', { route: r10('text', { callbackQueryId: null }), urgency: NONE, consent: accepted(), question: '¿aceptáis Sanitas?', handoffAwaiting: true }, H('text', null, { urgent: false })],
  ['a text that is an urgency while a handoff waits → text, urgent (RH5)', { route: r10('text', { callbackQueryId: null }), urgency: URGENT, consent: accepted(), question: 'me sangra mucho la encía', handoffAwaiting: true }, H('text', null, { urgent: true })],
  ['a complaint phrase while a handoff waits → the text for reception, not a new handoff', { route: r10('text', { callbackQueryId: null }), urgency: NONE, consent: accepted(), question: 'quiero poner una queja', handoffAwaiting: true }, H('text', null, { urgent: false })],
  ['an ordinary text with consent → B, unchanged', { route: r10('text', { callbackQueryId: null }), urgency: NONE, consent: accepted(), question: '¿cuánto cuesta una limpieza?' }, { action: 'core', text: null, keyboard: null }],
  ['👍 with consent → rating up (RH17)', { route: r10('rating', { value: 'up' }), urgency: null, consent: accepted() }, { action: 'rating', text: null, keyboard: null, value: 'up' }],
  ['👎 with consent → rating down', { route: r10('rating', { value: 'down' }), urgency: null, consent: accepted() }, { action: 'rating', text: null, keyboard: null, value: 'down' }],
  ['👍 without consent → the notice, nothing counted (RH18)', { route: r10('rating', { value: 'up' }), urgency: null, consent: {} }, NOTICE],
];
check('SPEC-010: decide — handoff, complaint, rating', () => {
  const decide = requireFn('decide');
  const wrong = [];
  for (const [name, input, expected] of HANDOFF_CASES) {
    let got;
    try { got = decide(input); } catch (e) { got = `throws: ${e.message}`; }
    if (JSON.stringify(got) !== JSON.stringify(expected)) wrong.push(`  ${name}\n    expected ${JSON.stringify(expected)}\n    got      ${JSON.stringify(got)}`);
  }
  if (wrong.length) throw new Error(`${wrong.length}/${HANDOFF_CASES.length} cases wrong:\n${wrong.join('\n')}`);
});
check('SPEC-010: every new callback fits in 64 bytes', () => {
  for (const d of ['handoff:a', 'handoff:u', 'handoff:p', 'handoff:q', 'hs:q', 'hn', 'rt:u', 'rt:d', 'hc:R-7KQ3']) {
    if (Buffer.byteLength(d) > 64) throw new Error(d);
  }
});

// --- Sync with the exported workflow A (C23, C25) ---
check('n8n nodes of A carry this exact code', () => {
  if (!fs.existsSync(EXPORT_PATH)) { console.log('SKIP sync check: no export of A'); return; }
  const wf = JSON.parse(fs.readFileSync(EXPORT_PATH, 'utf8'));
  const nodes = (Array.isArray(wf) ? wf[0] : wf).nodes;
  // SPEC-008: this module gained the cancel buttons without consent in M1, and A's export gets them
  // in M4. Until A has «Componer retirada», «Clasificar» and «Decidir» still carry the SPEC-007
  // module, so the check waits.
  if (!nodes.some((n) => n.name === 'Componer retirada')) {
    console.log("SKIP sync check: A's export has no SPEC-008 nodes yet; consentimiento.js is checked against it from SPEC-008 M4 (hasta M4)");
    return;
  }
  // SPEC-010: the module gains the handoff, complaint, rating and group routes in H1; A gets them in H4.
  if (!nodes.some((n) => n.name === 'Grupo de recepción')) {
    console.log("SKIP sync check: A's export has no SPEC-010 nodes yet; consentimiento.js is checked against it from SPEC-010 H4 (hasta H4)");
    return;
  }
  for (const name of NODE_NAMES) {
    const node = nodes.find((n) => n.name === name);
    if (!node) { console.log(`SKIP sync check: node "${name}" not in A's export yet`); continue; }
    if (!node.parameters.jsCode.startsWith(source)) throw new Error(`"${name}" jsCode does not start with consentimiento.js`);
    console.log(`sync check run: "${name}" in lifecenter-telegram-demo.json`);
  }
});

console.log(`
== SPEC-010 complaint report: ${complaintPositives.length} positives, ${complaintNegatives.length} negatives | handoff cases: ${HANDOFF_CASES.length}`);
console.log(`\n== SPEC-006 consent report\ndecision cases: ${CASES.length} | SPEC-007 booking cases: ${BOOKING_CASES.length} | SPEC-008 change cases: ${CHANGE_CASES.length}`);
console.log(failures ? `\nRED: ${failures} check(s) failed` : '\nGREEN: all checks passed');
process.exit(failures ? 1 : 0);
