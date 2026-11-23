// SPEC-006 consent module (specs/006-consent/spec.md, plan.md Step 1).
// Paste-ready: the n8n Code nodes "Clasificar" and "Decidir" of lifecenter-telegram-demo carry this
// exact code followed only by their input/output wiring (C23). No require, no network, no state.

// --- Configuration (C22). Change the version whenever CONSENT_NOTICE changes: everyone is asked again.
const CONSENT_TEXT_VERSION = '1';

// --- Fixed texts (spec "Fixed texts", approved by the human 2026-11-21) ---
const CONSENT_NOTICE =
  'Hola, soy el asistente de LifeCenter. Para responderte: quito tu nombre, teléfono, DNI y email ' +
  'de los mensajes antes de procesarlos; envío la consulta a un modelo de IA externo (Gemini, de ' +
  'Google), y guardo el recorrido de cada consulta, sin tus datos, durante 30 días. Si me cuentas un ' +
  'síntoma te daré siempre el teléfono de la clínica. Esto es una demostración: no escribas datos ' +
  'reales. ¿Aceptas?';
const ACCEPTED_TEXT = 'Gracias. Ya puedes escribirme tu consulta.';
const REJECTED_TEXT =
  'De acuerdo, no procesaré tus consultas. Puedes llamar a recepción. Si cambias de opinión, escribe /privacidad.';
const REVOKED_TEXT =
  'He retirado tu consentimiento. No procesaré más consultas tuyas. Si cambias de opinión, escribe /privacidad.';
const STATUS_ACCEPTED = 'Estado: aceptaste este aviso el {fecha}.';
const STATUS_NONE = 'Estado: no has aceptado este aviso.';
// Copies of CHG-001 texts this module now composes: D7 (error) and D12 (no text).
const ERROR_TEXT = 'Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?';
const TEXT_ONLY_TEXT = 'Solo puedo leer mensajes de texto. ¿Me escribes tu consulta?';

// --- Buttons (C7): labels and callback_data, each at most 64 bytes ---
const BUTTON_LABELS = {
  handoff: 'Hablar con recepción',
  accept: 'Acepto',
  reject: 'No acepto',
  withdraw: 'Retirar consentimiento',
};
const CALLBACK_HANDOFF = 'handoff';
const CALLBACK_WITHDRAW = 'consent:withdraw';
const callbackAccept = (version = CONSENT_TEXT_VERSION) => `consent:accept:${version}`;
const callbackReject = (version = CONSENT_TEXT_VERSION) => `consent:reject:${version}`;

// --- Commands (spec "Command"): exactly /start or /privacidad, optionally @<bot>, spaces ignored,
// in any letter case (phone keyboards capitalize the first letter) ---
// SPEC-007: /cita and /micita are booking commands (any letter case, like the others).
const COMMAND = /^\s*\/(start|privacidad|cita|micita)(?:@[A-Za-z0-9_]+)?\s*$/i;
const BOOKING_COMMANDS = ['cita', 'micita'];
function parseCommand(text) {
  const m = COMMAND.exec(typeof text === 'string' ? text : '');
  return m ? m[1].toLowerCase() : null;
}

// --- Buttons: callback_data → { kind, version } ---
const CONSENT_CALLBACK = /^consent:(accept|reject):(.+)$/;
function parseCallback(data) {
  if (data === CALLBACK_HANDOFF) return { kind: 'handoff', version: null };
  if (data === CALLBACK_WITHDRAW) return { kind: 'withdraw', version: null };
  if (typeof data === 'string' && data.startsWith('bk:')) return { kind: 'booking_button', version: null }; // SPEC-007
  const m = CONSENT_CALLBACK.exec(typeof data === 'string' ? data : '');
  return m ? { kind: m[1], version: m[2] } : { kind: 'unknown_button', version: null };
}

// --- A Telegram update → route. fromId is a string: it is only ever passed to Neon as $1 (C18). ---
function classifyUpdate(update) {
  const asId = (v) => (v === undefined || v === null ? null : String(v));
  const cq = update && update.callback_query;
  if (cq) {
    const { kind, version } = parseCallback(cq.data);
    const route = {
      kind,
      fromId: asId(cq.from && cq.from.id),
      chatId: cq.message && cq.message.chat ? cq.message.chat.id : null,
      callbackQueryId: cq.id === undefined ? null : cq.id,
      version,
    };
    return kind === 'booking_button' ? { ...route, data: cq.data } : route; // SPEC-007
  }
  const m = (update && update.message) || {};
  const hasText = typeof m.text === 'string' && m.text !== '';
  const command = hasText ? parseCommand(m.text) : null;
  const booking = BOOKING_COMMANDS.includes(command);
  const route = {
    kind: booking ? 'booking_command' : command || (hasText ? 'text' : 'other'),
    fromId: asId(m.from && m.from.id),
    chatId: m.chat ? m.chat.id : null,
    callbackQueryId: null,
    version: null,
  };
  return booking ? { ...route, data: command } : route; // SPEC-007: /cita, /micita
}

// --- SPEC-008 MC10: the only booking buttons allowed without consent (one start code each) ---
const CANCEL_WITHOUT_CONSENT = /^bk:(?:a|ac|v):[0-9a-z]{1,8}$/;

// --- Consent in force (C22): accepted with the current version; anything else is no consent ---
function isConsentInForce(row) {
  return !!row && row.status === 'accepted' && row.text_version === CONSENT_TEXT_VERSION;
}

// --- dd/mm/aaaa in Europe/Madrid ---
function formatDate(decidedAt) {
  const parts = new Intl.DateTimeFormat('es-ES', {
    timeZone: 'Europe/Madrid', day: '2-digit', month: '2-digit', year: 'numeric',
  }).formatToParts(new Date(decidedAt));
  const get = (type) => parts.find((p) => p.type === type).value;
  return `${get('day')}/${get('month')}/${get('year')}`;
}

// --- What to do with an update (plan Step 1, decision table; C2–C16) ---
// urgency: the output of "Detectar urgencia" (B's wiring), or null if it did not run.
// consent: the row from consent_get ({} when there is none); lookupFailed: the lookup errored.
function decide({ route, urgency, consent, lookupFailed }) {
  const reply = (text, keyboard) => ({ action: 'reply', text, keyboard });
  const notice = reply(CONSENT_NOTICE, 'consent');
  const inForce = !lookupFailed && isConsentInForce(consent);
  const kind = route && route.kind;

  if (kind === 'handoff') throw new Error('decide(): the handoff button has its own branch (C12)');
  if (kind === 'text') {
    if (inForce) return { action: 'core', text: null, keyboard: null };
    if (urgency && urgency.urgency_level && urgency.urgency_level !== 'none') return reply(urgency.text, 'handoff');
    return lookupFailed ? reply(ERROR_TEXT, 'handoff') : notice;
  }
  if (lookupFailed) return reply(ERROR_TEXT, 'handoff');

  const withStatus = (status, keyboard) => reply(`${CONSENT_NOTICE}\n\n${status}`, keyboard);
  switch (kind) {
    case 'other':
      return inForce ? reply(TEXT_ONLY_TEXT, 'none') : notice;
    case 'start':
    case 'privacidad':
      if (inForce) return withStatus(STATUS_ACCEPTED.replace('{fecha}', formatDate(consent.decided_at)), 'withdraw');
      return kind === 'start' ? notice : withStatus(STATUS_NONE, 'consent');
    case 'accept':
      return route.version === CONSENT_TEXT_VERSION ? { action: 'accept', text: ACCEPTED_TEXT, keyboard: 'none' } : notice;
    case 'reject':
      return route.version === CONSENT_TEXT_VERSION ? reply(REJECTED_TEXT, 'none') : notice;
    case 'withdraw':
      return { action: 'withdraw', text: REVOKED_TEXT, keyboard: 'none' };
    case 'booking_command': // SPEC-007 BK8: every booking step needs consent in force
    case 'booking_button':
      if (inForce) return { action: 'booking', text: null, keyboard: null, consent: true };
      // SPEC-008 MC10: without consent, only «Anular» (bk:a), «Sí, anular» (bk:ac) and the «Mantener
      // mi cita» of the cancel confirmation (bk:v with a start) go through, flagged consent: false.
      if (kind === 'booking_button' && CANCEL_WITHOUT_CONSENT.test(route.data || '')) {
        return { action: 'booking', text: null, keyboard: null, consent: false };
      }
      return notice;
    case 'unknown_button':
      return notice;
    default:
      throw new Error(`decide(): unknown route kind "${kind}"`);
  }
}
