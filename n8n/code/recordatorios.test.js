// SPEC-009 tests for n8n/code/recordatorios.js (specs/010-reminders/plan.md Step 1).
// Run: node n8n/code/recordatorios.test.js   — no dependencies; exits non-zero on any failure.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_PATH = path.join(__dirname, 'recordatorios.js');
const EXPORT_PATH = path.join(ROOT, 'n8n', 'workflows', 'lifecenter-reminders.json');
const NODE_NAMES = ['Componer recordatorio', 'Clasificar error'];

// Spec texts (spec.md "Fixed texts", approved 2026-11-23), typed here independently of the source.
const T = {
  REMINDER: 'Recordatorio de LifeCenter: tienes una cita {cuando}, a las {hora}, en {direccion}. Si no puedes venir, puedes cambiarla o anularla aquí.',
};
const LABELS = { ire: 'Iré', cambiar: 'Cambiar', anular: 'Anular', recepcion: 'Hablar con recepción' };

const source = fs.existsSync(SOURCE_PATH) ? fs.readFileSync(SOURCE_PATH, 'utf8').replace(/\r\n/g, '\n') : '';
const EXPORTED = ['TEXTS', 'LABELS', 'CLINIC_ADDRESS', 'CLINIC_ADDRESS_IS_EXAMPLE', 'whenText', 'composeReminder',
  'classifySendError', 'CONSENT_TEXT_VERSION'];
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
  if (typeof M[name] !== 'function') throw new Error(`${name} is not implemented in recordatorios.js`);
  return M[name];
}
const code = (iso) => Math.round(Date.parse(iso) / 60000).toString(36); // independent of the source

// "now" is Monday 30 Nov 2026, 10:00 Madrid (UTC+1).
const NOW = '2026-11-30T09:00:00.000Z';
const TOMORROW = '2026-12-01T08:00:00.000Z'; // martes 1 de diciembre, 9:00
const TODAY = '2026-11-30T15:30:00.000Z'; // lunes 30 de noviembre, 16:30
const LATER = '2026-12-03T15:00:00.000Z'; // jueves 3 de diciembre, 16:00

// === Texts and the example address (RM18; clarifications Q5) ===

check('fixed texts', () => eq((M.TEXTS || {}).REMINDER, T.REMINDER, 'TEXTS.REMINDER'));
check('button labels', () => eq(M.LABELS, LABELS, 'LABELS'));
check('the clinic address is an example value until DEP-01', () => {
  if (typeof M.CLINIC_ADDRESS !== 'string' || !M.CLINIC_ADDRESS.trim()) throw new Error('CLINIC_ADDRESS missing');
  eq(M.CLINIC_ADDRESS_IS_EXAMPLE, true, 'CLINIC_ADDRESS_IS_EXAMPLE');
});

// === {cuándo}: tomorrow, today, later; both DST changes (Europe/Madrid) ===

check('whenText', () => {
  const w = requireFn('whenText');
  eq(w(TOMORROW, NOW), 'mañana, martes 1 de diciembre', 'tomorrow');
  eq(w(TODAY, NOW), 'hoy, lunes 30 de noviembre', 'today (a late reminder)');
  eq(w(LATER, NOW), 'el jueves 3 de diciembre', 'later');
  // March 2027: the clocks go forward on Sunday 28. Now Saturday 27, 20:30 Madrid (UTC+1).
  eq(w('2027-03-28T07:00:00.000Z', '2027-03-27T19:30:00.000Z'), 'mañana, domingo 28 de marzo', 'March change');
  // Now Saturday 27, 23:30 Madrid: Monday 29 is the day after tomorrow.
  eq(w('2027-03-29T07:00:00.000Z', '2027-03-27T22:30:00.000Z'), 'el lunes 29 de marzo', 'March, two days');
  // October 2027: the clocks go back on Sunday 31. Now Sunday 31, 00:30 Madrid (UTC+2).
  eq(w('2027-11-01T08:00:00.000Z', '2027-10-30T22:30:00.000Z'), 'mañana, lunes 1 de noviembre', 'October change');
  // New year: the year is added only when it is not the current one.
  eq(w('2027-01-04T08:00:00.000Z', '2026-12-31T10:00:00.000Z'), 'el lunes 4 de enero de 2027', 'next year');
  eq(w('2027-01-01T09:00:00.000Z', '2026-12-31T10:00:00.000Z'), 'mañana, viernes 1 de enero de 2027', 'tomorrow, next year');
});

// === The reminder message (RM18): no type, the date, the time, the address, 4 buttons ===

check('composeReminder', () => {
  const c = requireFn('composeReminder');
  const row = { id: 7, chat_id: '900951', starts_at: TOMORROW, ends_at: '2026-12-01T08:45:00.000Z' };
  const fill = (t, v) => Object.entries(v).reduce((s, [k, x]) => s.replace(`{${k}}`, x), t);
  eq(c(row, NOW), {
    text: fill(T.REMINDER, { cuando: 'mañana, martes 1 de diciembre', hora: '9:00', direccion: M.CLINIC_ADDRESS }),
    rows: [
      [{ text: LABELS.ire, data: `bk:i:${code(TOMORROW)}` }],
      [{ text: LABELS.cambiar, data: `bk:x:${code(TOMORROW)}` }],
      [{ text: LABELS.anular, data: `bk:a:${code(TOMORROW)}` }],
      [{ text: LABELS.recepcion, data: 'handoff' }],
    ],
  }, 'tomorrow');
  eq(c({ ...row, starts_at: TODAY }, NOW).text,
    fill(T.REMINDER, { cuando: 'hoy, lunes 30 de noviembre', hora: '16:30', direccion: M.CLINIC_ADDRESS }), 'today');
});
check('the reminder never shows the appointment type, and every callback fits in 64 bytes', () => {
  const c = requireFn('composeReminder');
  const r = c({ id: 1, chat_id: '900951', starts_at: '2099-12-31T22:45:00.000Z', ends_at: '2099-12-31T23:30:00.000Z' }, NOW);
  if (/limpieza|revisi[oó]n|primera visita|blanqueamiento|implante|ortodoncia/i.test(r.text)) throw new Error(`type in «${r.text}»`);
  if (r.rows.length !== 4 || r.rows.some((row) => row.length !== 1)) throw new Error('4 rows of one button expected');
  for (const row of r.rows) for (const b of row) {
    if (Buffer.byteLength(b.data, 'utf8') > 64) throw new Error(`"${b.data}" too long`);
  }
});

// === Telegram errors (RM17) ===

check('classifySendError', () => {
  const k = requireFn('classifySendError');
  eq(k({ message: 'Forbidden: bot was blocked by the user', httpCode: '403' }), 'blocked', '403 blocked');
  eq(k({ message: 'Bad Request: chat not found', httpCode: '400' }), 'blocked', 'chat not found');
  eq(k({ message: 'Forbidden: user is deactivated' }), 'blocked', 'deactivated');
  eq(k('403 - {"ok":false,"error_code":403,"description":"Forbidden: bot was blocked by the user"}'), 'blocked', 'n8n string form');
  // Human, 2026-11-24 (Q8: better a missing reminder than a duplicate): only a 429 is surely not
  // delivered, so only a 429 is retried. A 5xx or a network error may have been delivered: failed.
  eq(k({ message: 'Too Many Requests: retry after 5', httpCode: '429' }), 'retry', '429');
  eq(k('429 - {"ok":false,"error_code":429,"description":"Too Many Requests: retry after 5"}'), 'retry', '429 string form');
  eq(k({ message: 'Internal Server Error', httpCode: '500' }), 'failed', '500');
  eq(k({ message: 'Bad Gateway', httpCode: '502' }), 'failed', '502');
  eq(k({ message: 'connect ETIMEDOUT' }), 'failed', 'network timeout');
  eq(k({ message: 'socket hang up' }), 'failed', 'network reset');
  eq(k({ message: 'Bad Request: message text is empty', httpCode: '400' }), 'failed', 'other 400');
  eq(k(undefined), 'failed', 'unknown');
  eq(k({ message: 'Request timed out after 4290 ms' }), 'failed', 'a number containing 429 is not a 429');
});

// === Consent version (human, 2026-11-24): C passes it to reminder_claim_due ===

check('CONSENT_TEXT_VERSION equals the one of consentimiento.js', () => {
  const own = M.CONSENT_TEXT_VERSION;
  if (typeof own !== 'string' || !own) throw new Error('CONSENT_TEXT_VERSION missing or not a string');
  const consentSource = fs.readFileSync(path.join(__dirname, 'consentimiento.js'), 'utf8');
  const m = consentSource.match(/^const CONSENT_TEXT_VERSION = '([^']*)';$/m);
  if (!m) throw new Error('CONSENT_TEXT_VERSION not found in consentimiento.js');
  eq(own, m[1], 'consent text version');
});

// === Sync with the exported workflow C (RM27) ===

check('n8n nodes of C carry this exact code', () => {
  if (!fs.existsSync(EXPORT_PATH)) { console.log("SKIP sync check: workflow C has no export yet; recordatorios.js is checked against it from SPEC-009 N4 (hasta N4)"); return; }
  const nodes = (JSON.parse(fs.readFileSync(EXPORT_PATH, 'utf8'))[0] || {}).nodes || [];
  for (const name of NODE_NAMES) {
    const node = nodes.find((n) => n.name === name);
    if (!node) throw new Error(`node "${name}" missing in C's export`);
    if (!node.parameters.jsCode.startsWith(source)) throw new Error(`"${name}" jsCode does not start with recordatorios.js`);
    console.log(`sync check run: "${name}" in lifecenter-reminders.json`);
  }
  // Human, 2026-11-24: the claim passes this module's CONSENT_TEXT_VERSION, which equals consentimiento.js.
  const claim = nodes.find((n) => n.name === 'Reclamar recordatorios');
  if (!claim) throw new Error('node "Reclamar recordatorios" missing in C\'s export');
  eq(claim.parameters.options.queryReplacement, M.CONSENT_TEXT_VERSION, 'version passed to reminder_claim_due');
  console.log('sync check run: "Reclamar recordatorios" passes CONSENT_TEXT_VERSION');
});

console.log(failures ? `\nRED: ${failures} check(s) failed` : '\nGREEN: all checks passed');
process.exit(failures ? 1 : 0);
