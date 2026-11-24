// SPEC-009 reminders module (specs/010-reminders/spec.md, plan.md Step 1).
// Paste-ready: the n8n Code nodes «Componer recordatorio» and «Clasificar error» of lifecenter-reminders
// carry this exact code followed only by their wiring (RM27). No require, no network, no state.

// --- Fixed texts (spec "Fixed texts", approved by the human 2026-11-23) ---
const TEXTS = {
  REMINDER: 'Recordatorio de LifeCenter: tienes una cita {cuando}, a las {hora}, en {direccion}. Si no puedes venir, puedes cambiarla o anularla aquí.',
};
const LABELS = { ire: 'Iré', cambiar: 'Cambiar', anular: 'Anular', recepcion: 'Hablar con recepción' };
const CALLBACK_HANDOFF = 'handoff';

// --- The clinic's address (clarifications Q5): an example value until LifeCenter provides it (DEP-01).
// To set the real one, change CLINIC_ADDRESS, set CLINIC_ADDRESS_IS_EXAMPLE to false, and paste this
// file into C's two Code nodes again (keeping their wiring).
const CLINIC_ADDRESS = 'Calle de Ejemplo 1, Madrid';
const CLINIC_ADDRESS_IS_EXAMPLE = true;

// --- The consent notice version (SPEC-006 C22): the same value as consentimiento.js, checked by a test.
// C passes it to reminder_claim_due, which skips anyone without consent in force for this version.
const CONSENT_TEXT_VERSION = '1';

// --- Madrid dates: the same rules as citas.js (Q15 of SPEC-007), kept here so C needs no other module ---
const WEEKDAYS_LONG = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const MONTHS_LONG = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
  'octubre', 'noviembre', 'diciembre'];
function madridParts(value) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Madrid', year: 'numeric', month: 'numeric', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(value));
  const get = (type) => parseInt(parts.find((p) => p.type === type).value, 10);
  const y = get('year');
  const mo = get('month');
  const d = get('day');
  const weekday = (new Date(Date.UTC(y, mo - 1, d)).getUTCDay() + 6) % 7; // 0 = Monday
  return { y, mo, d, h: get('hour'), mi: get('minute'), weekday };
}
function hourOf(value) {
  const p = madridParts(value);
  return `${p.h}:${String(p.mi).padStart(2, '0')}`;
}
function longDate(value, now) {
  const p = madridParts(value);
  const year = p.y !== madridParts(now).y ? ` de ${p.y}` : '';
  return `${WEEKDAYS_LONG[p.weekday]} ${p.d} de ${MONTHS_LONG[p.mo - 1]}${year}`;
}
// Whole Madrid calendar days from now's date to value's date (0 = today, 1 = tomorrow).
function madridDayDiff(value, now) {
  const a = madridParts(value);
  const b = madridParts(now);
  return Math.round((Date.UTC(a.y, a.mo - 1, a.d) - Date.UTC(b.y, b.mo - 1, b.d)) / 86400000);
}
// {cuándo} of REMINDER_TEXT: «mañana, martes 1 de diciembre», «hoy, …» for a late reminder, or the full date.
function whenText(start, now) {
  const diff = madridDayDiff(start, now);
  const date = longDate(start, now);
  if (diff === 0) return `hoy, ${date}`;
  if (diff === 1) return `mañana, ${date}`;
  return `el ${date}`;
}

// --- The reminder message (RM18): no appointment type; «Iré», «Cambiar», «Anular», reception ---
// row: what reminder_claim_due returns ({ id, chat_id, starts_at, ends_at }). The callbacks are the ones
// A understands: bk:i (SPEC-009), bk:x and bk:a (SPEC-008), each with the appointment's start code.
const startCode = (start) => Math.round(new Date(start).getTime() / 60000).toString(36);
function composeReminder(row, now) {
  const code = startCode(row.starts_at);
  const text = TEXTS.REMINDER
    .replace('{cuando}', whenText(row.starts_at, now))
    .replace('{hora}', hourOf(row.starts_at))
    .replace('{direccion}', CLINIC_ADDRESS);
  return {
    text,
    rows: [
      [{ text: LABELS.ire, data: `bk:i:${code}` }],
      [{ text: LABELS.cambiar, data: `bk:x:${code}` }],
      [{ text: LABELS.anular, data: `bk:a:${code}` }],
      [{ text: LABELS.recepcion, data: CALLBACK_HANDOFF }],
    ],
  };
}

// --- Telegram errors (RM17; human, 2026-11-24, Q8: better a missing reminder than a duplicate) ---
// blocked: the patient blocked the bot or the chat is gone (never retried).
// retry:   only a 429, the one error where Telegram surely did not deliver the message.
// failed:  anything else (5xx, network, unknown): it may have been delivered, so it is never retried.
function classifySendError(error) {
  const text = typeof error === 'string' ? error : JSON.stringify(error || {});
  if (/\b403\b|forbidden|blocked by the user|chat not found|user is deactivated/i.test(text)) return 'blocked';
  if (/(?<![0-9])429(?![0-9])|too many requests/i.test(text)) return 'retry';
  return 'failed';
}

// --- The Telegram node's inlineKeyboard, from the rows (the same shape as citas.js) ---
function toTelegramKeyboard(rows) {
  return {
    rows: rows.map((r) => ({ row: { buttons: r.map((b) => ({ text: b.text, additionalFields: { callback_data: b.data } })) } })),
  };
}
