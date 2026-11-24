// SPEC-010 tests for n8n/code/recepcion.js (specs/011-reception-handoff/plan.md Step 1).
// Run: node n8n/code/recepcion.test.js   — no dependencies; exits non-zero on any failure.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_PATH = path.join(__dirname, 'recepcion.js');
const EXPORT_PATH = path.join(ROOT, 'n8n', 'workflows', 'lifecenter-telegram-demo.json');
const NODE_NAMES = ['Recepción', 'Grupo de recepción'];

// Spec texts (spec.md "Fixed texts", verified 2026-11-24), typed here independently of the source.
const T = {
  HANDOFF_CONFIRM: '¿Quieres que pase tu consulta a recepción? Te pediré que la escribas en un mensaje; la leerán sin tu nombre ni tu teléfono.',
  HANDOFF_WRITE: 'Escribe en un mensaje lo que quieres que lea recepción. No incluyas datos personales.',
  HANDOFF_SENT: 'Hecho. He pasado tu consulta a recepción (código {codigo}). Te responderán por aquí en horario de la clínica.',
  HANDOFF_CANCELLED: 'De acuerdo, no paso nada a recepción.',
  HANDOFF_FAILED: 'Ahora mismo no puedo pasar tu consulta. Llama a recepción en horario de atención.',
  GROUP_HEADER: '[{codigo}] Motivo: {motivo}',
  GROUP_FOOTER: 'Responde a este mensaje para contestar al paciente.',
  RECEPTION_REPLY: 'Recepción de LifeCenter ({codigo}): {texto}',
  HANDOFF_CLOSED: 'Esta consulta ya está cerrada.',
  COMPLAINT_CONFIRM: 'Siento lo ocurrido. ¿Quieres que pase tu queja a recepción? Te pediré que la escribas en un mensaje; la leerán sin tu nombre ni tu teléfono.',
  RATING_THANKS: 'Gracias por tu valoración.',
};
const LABELS = { si: 'Sí, pasar a recepción', no: 'No', cerrar: 'Cerrar', cerrada: 'Cerrada', up: '👍', down: '👎' };

const source = fs.existsSync(SOURCE_PATH) ? fs.readFileSync(SOURCE_PATH, 'utf8').replace(/\r\n/g, '\n') : '';
const EXPORTED = ['TEXTS', 'LABELS', 'REASONS', 'CODE_ALPHABET', 'CODE_PATTERN', 'handoffReasonFor', 'confirmView',
  'groupMessage', 'groupAction', 'receptionReply', 'sentText', 'answerRows', 'toTelegramKeyboard'];
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
  if (typeof M[name] !== 'function') throw new Error(`${name} is not implemented in recepcion.js`);
  return M[name];
}
const bytes = (s) => Buffer.byteLength(s, 'utf8');
const allData = (rows) => rows.flat().map((b) => b.data);

// === Texts, labels, reasons ===
check('fixed texts', () => { for (const k of Object.keys(T)) eq((M.TEXTS || {})[k], T[k], k); });
check('labels', () => eq(M.LABELS, LABELS, 'LABELS'));
check('reasons (RH2, RH13)', () => eq(M.REASONS, { a: 'abstención', u: 'urgencia', p: 'petición', q: 'queja' }, 'REASONS'));

// === The reason of the handoff button, from B's reply (RH2; B does not change) ===
check('handoffReasonFor', () => {
  const f = requireFn('handoffReasonFor');
  eq(f({ reason: 'urgency' }), 'u', 'urgency');
  for (const r of ['below_threshold', 'model_abstained', 'validation_failed']) eq(f({ reason: r }), 'a', r);
  for (const r of ['llm_error', 'answered', undefined]) eq(f({ reason: r }), 'p', String(r));
});

// === The confirmation (RH1, RH13) ===
check('confirmView: handoff and complaint', () => {
  const f = requireFn('confirmView');
  eq(f('a'), { text: T.HANDOFF_CONFIRM, rows: [[{ text: LABELS.si, data: 'hs:a' }], [{ text: LABELS.no, data: 'hn' }]] }, 'abstention');
  eq(f('p').rows[0][0].data, 'hs:p', 'request');
  eq(f('u').rows[0][0].data, 'hs:u', 'urgency');
  eq(f('q'), { text: T.COMPLAINT_CONFIRM, rows: [[{ text: LABELS.si, data: 'hs:q' }], [{ text: LABELS.no, data: 'hn' }]] }, 'complaint');
});

// === The code (P3): prefix and alphabet with no look-alikes ===
check('code alphabet and pattern', () => {
  eq(M.CODE_ALPHABET, 'ABCDEFGHJKMNPQRSTUVWXYZ23456789', 'alphabet (no 0, O, 1, I, L)');
  const re = M.CODE_PATTERN;
  if (!(re instanceof RegExp)) throw new Error('CODE_PATTERN missing');
  for (const ok of ['R-7KQ3', 'Q-ABCD', 'R-2345']) if (!re.test(ok)) throw new Error(`rejects ${ok}`);
  for (const bad of ['R-7KQ', 'X-7KQ3', 'R-7KQ0', 'R-OKQ3', 'r-7kq3', 'R-7KQ3 ', 'R-1KQ3', 'R-LKQ3']) if (re.test(bad)) throw new Error(`accepts ${bad}`);
});

// === The group message (RH4, RH5, P4): no name, phone, user or appointment; «Cerrar» ===
check('groupMessage', () => {
  const f = requireFn('groupMessage');
  const g = f({ code: 'R-7KQ3', reason: 'a', text: '¿Aceptáis el seguro de [NOMBRE]?', urgent: false });
  eq(g, { text: '[R-7KQ3] Motivo: abstención\n\n¿Aceptáis el seguro de [NOMBRE]?\n\nResponde a este mensaje para contestar al paciente.',
    rows: [[{ text: LABELS.cerrar, data: 'hc:R-7KQ3' }]] }, 'abstention');
  eq(f({ code: 'Q-ABCD', reason: 'q', text: 'el trato fue malo', urgent: false }).text.split('\n')[0], '[Q-ABCD] Motivo: queja', 'complaint');
  eq(f({ code: 'R-2345', reason: 'p', text: 'me sangra la encía', urgent: true }).text.split('\n')[0], '[R-2345] Motivo: urgencia', 'urgency wins (RH5)');
});

// === What the patient gets (RH4, RH9) ===
check('sentText and receptionReply', () => {
  eq(requireFn('sentText')('R-7KQ3'), T.HANDOFF_SENT.replace('{codigo}', 'R-7KQ3'), 'sent');
  eq(requireFn('receptionReply')('R-7KQ3', 'Sí, aceptamos Sanitas.'), 'Recepción de LifeCenter (R-7KQ3): Sí, aceptamos Sanitas.', 'reply');
});

// === Updates from groups (RH9–RH12): only replies to the bot and «Cerrar» in the reception group ===
const RG = '-1001234567890'; // a fake reception group id
const groupMsg = (o) => ({ kind: 'group', chatId: RG, messageId: 50, replyToMessageId: null, replyToBot: false, text: 'hola', callbackData: null, callbackQueryId: null, ...o });
check('groupAction', () => {
  const f = requireFn('groupAction');
  eq(f(groupMsg({ replyToMessageId: 41, replyToBot: true, text: 'Sí, aceptamos Sanitas.' }), RG),
    { action: 'forward', replyToMessageId: 41, text: 'Sí, aceptamos Sanitas.' }, 'reply to the bot');
  eq(f(groupMsg({ text: 'buenos días' }), RG), { action: 'ignore' }, 'a staff message that is not a reply');
  eq(f(groupMsg({ replyToMessageId: 41, replyToBot: false, text: 'ok' }), RG), { action: 'ignore' }, 'a reply to a person');
  eq(f(groupMsg({ replyToMessageId: 41, replyToBot: true, text: null }), RG), { action: 'ignore' }, 'a sticker as reply');
  eq(f(groupMsg({ replyToMessageId: 41, replyToBot: true, text: '   ' }), RG), { action: 'ignore' }, 'an empty reply');
  eq(f(groupMsg({ text: null, callbackData: 'hc:R-7KQ3', callbackQueryId: 'cq-9' }), RG),
    { action: 'close', code: 'R-7KQ3', callbackQueryId: 'cq-9', messageId: 50 }, '«Cerrar»');
  eq(f(groupMsg({ text: null, callbackData: 'hc:R-7KQ0', callbackQueryId: 'cq-9' }), RG), { action: 'ignore' }, 'a malformed code');
  eq(f(groupMsg({ chatId: '-1009999999999', replyToMessageId: 41, replyToBot: true, text: 'x' }), RG), { action: 'ignore' }, 'another group');
  eq(f(groupMsg({ chatId: '-1009999999999', text: null, callbackData: 'hc:R-7KQ3' }), RG), { action: 'ignore' }, '«Cerrar» in another group');
  eq(f(groupMsg({ replyToMessageId: 41, replyToBot: true, text: 'x' }), null), { action: 'ignore' }, 'no reception group registered');
  eq(f(groupMsg({ chatId: '-100', replyToMessageId: 41, replyToBot: true, text: 'x' }), ''), { action: 'ignore' }, 'an empty registered id');
});

// === The keyboard under B's replies (RH2, RH16): reason in «Hablar con recepción», 👍/👎 only under `answered` ===
check('answerRows', () => {
  const f = requireFn('answerRows');
  eq(f({ reason: 'answered', handoff: false, offer_booking: false }), [[{ text: '👍', data: 'rt:u' }, { text: '👎', data: 'rt:d' }]], 'answered');
  eq(f({ reason: 'answered', handoff: false, offer_booking: true }),
    [[{ text: 'Pedir cita', data: 'bk:menu' }], [{ text: '👍', data: 'rt:u' }, { text: '👎', data: 'rt:d' }]], 'answered with a price');
  eq(f({ reason: 'model_abstained', handoff: true, offer_booking: false }), [[{ text: 'Hablar con recepción', data: 'handoff:a' }]], 'abstention');
  eq(f({ reason: 'urgency', handoff: true, offer_booking: false }), [[{ text: 'Hablar con recepción', data: 'handoff:u' }]], 'urgency');
  eq(f({ reason: 'llm_error', handoff: true, offer_booking: false }), [[{ text: 'Hablar con recepción', data: 'handoff:p' }]], 'error');
  eq(f({ reason: 'below_threshold', handoff: true, offer_booking: false }).flat().some((b) => b.data.startsWith('rt:')), false, 'no rating under an abstention');
});

check('every callback fits in 64 bytes', () => {
  const rows = [
    ...['a', 'u', 'p', 'q'].flatMap((r) => requireFn('confirmView')(r).rows),
    ...requireFn('groupMessage')({ code: 'R-7KQ3', reason: 'a', text: 'x', urgent: false }).rows,
    ...requireFn('answerRows')({ reason: 'answered', handoff: false, offer_booking: true }),
  ];
  for (const d of allData(rows)) if (bytes(d) > 64) throw new Error(`${d} is ${bytes(d)} bytes`);
});

// === Sync with A (hasta H4) ===
check('n8n nodes of A carry this exact code', () => {
  const nodes = fs.existsSync(EXPORT_PATH) ? (JSON.parse(fs.readFileSync(EXPORT_PATH, 'utf8'))[0] || {}).nodes || [] : [];
  if (!nodes.some((n) => n.name === 'Grupo de recepción')) {
    console.log("SKIP sync check: A's export has no SPEC-010 nodes yet; recepcion.js is checked against it from SPEC-010 H4 (hasta H4)");
    return;
  }
  for (const name of NODE_NAMES) {
    const node = nodes.find((n) => n.name === name);
    if (!node) throw new Error(`node "${name}" missing in A's export`);
    if (!node.parameters.jsCode.startsWith(source)) throw new Error(`"${name}" jsCode does not start with recepcion.js`);
    console.log(`sync check run: "${name}" in lifecenter-telegram-demo.json`);
  }
});

console.log(failures ? `\nRED: ${failures} check(s) failed` : '\nGREEN: all checks passed');
process.exit(failures ? 1 : 0);
