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
// SPEC-010 (spec "Fixed texts", verified 2026-11-24): the D8 text, now chosen here, for a handoff without
// consent; and the reply to a complaint without consent.
const HANDOFF_NO_CONSENT_TEXT = 'Ahora mismo no puedo pasar tu consulta automáticamente. Llama a recepción en horario de atención.';
const COMPLAINT_NO_CONSENT_TEXT =
  'Para pasar tu queja a recepción necesito tu consentimiento (/privacidad). También puedes llamar a recepción en horario de atención.';

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
// SPEC-010: /queja opens the complaint path (RH13).
const COMMAND = /^\s*\/(start|privacidad|cita|micita|queja)(?:@[A-Za-z0-9_]+)?\s*$/i;
const BOOKING_COMMANDS = ['cita', 'micita'];
function parseCommand(text) {
  const m = COMMAND.exec(typeof text === 'string' ? text : '');
  return m ? m[1].toLowerCase() : null;
}

// --- Buttons: callback_data → { kind, version } ---
const CONSENT_CALLBACK = /^consent:(accept|reject):(.+)$/;
// SPEC-010 RH2, RH3, RH6, RH17: handoff:<reason> (the old `handoff` is a request), «Sí, pasar a
// recepción» (hs:<reason>), «No» (hn), and the ratings (rt:u / rt:d). «Cerrar» (hc:) only exists in groups.
const HANDOFF_CALLBACK = /^(handoff|hs):([aupq])$/;
const RATING_CALLBACK = /^rt:([ud])$/;
function parseCallback(data) {
  if (data === CALLBACK_HANDOFF) return { kind: 'handoff', version: null, reason: 'p' };
  const h = HANDOFF_CALLBACK.exec(typeof data === 'string' ? data : '');
  if (h) return { kind: h[1] === 'hs' ? 'handoff_confirm' : 'handoff', version: null, reason: h[2] };
  if (data === 'hn') return { kind: 'handoff_cancel', version: null };
  const rt = RATING_CALLBACK.exec(typeof data === 'string' ? data : '');
  if (rt) return { kind: 'rating', version: null, value: rt[1] === 'u' ? 'up' : 'down' };
  if (data === CALLBACK_WITHDRAW) return { kind: 'withdraw', version: null };
  if (typeof data === 'string' && data.startsWith('bk:')) return { kind: 'booking_button', version: null }; // SPEC-007
  const m = CONSENT_CALLBACK.exec(typeof data === 'string' ? data : '');
  return m ? { kind: m[1], version: m[2] } : { kind: 'unknown_button', version: null };
}

// --- A Telegram update → route. fromId is a string: it is only ever passed to Neon as $1 (C18). ---
function classifyUpdate(update) {
  const asId = (v) => (v === undefined || v === null ? null : String(v));
  const cq = update && update.callback_query;
  // SPEC-010 RH12, A3: anything from a chat that is not private is a group update. It never carries the
  // sender's id, and never reaches the consent logic.
  const chatOf = cq ? cq.message && cq.message.chat : update && update.message && update.message.chat;
  if (chatOf && chatOf.type && chatOf.type !== 'private') {
    const gm = cq ? cq.message : update.message;
    const reply = !cq && gm.reply_to_message;
    return {
      kind: 'group',
      chatId: asId(chatOf.id),
      messageId: gm && gm.message_id !== undefined ? gm.message_id : null,
      replyToMessageId: reply ? reply.message_id : null,
      replyToBot: !!(reply && reply.from && reply.from.is_bot),
      text: !cq && typeof gm.text === 'string' ? gm.text : null,
      callbackData: cq ? cq.data : null,
      callbackQueryId: cq && cq.id !== undefined ? cq.id : null,
    };
  }
  if (cq) {
    const parsed = parseCallback(cq.data);
    const route = {
      kind: parsed.kind,
      fromId: asId(cq.from && cq.from.id),
      chatId: cq.message && cq.message.chat ? cq.message.chat.id : null,
      callbackQueryId: cq.id === undefined ? null : cq.id,
      version: parsed.version,
    };
    if (parsed.kind === 'booking_button') return { ...route, data: cq.data }; // SPEC-007
    if ('reason' in parsed) return { ...route, reason: parsed.reason }; // SPEC-010
    if ('value' in parsed) return { ...route, value: parsed.value };
    return route;
  }
  const m = (update && update.message) || {};
  const hasText = typeof m.text === 'string' && m.text !== '';
  const command = hasText ? parseCommand(m.text) : null;
  const booking = BOOKING_COMMANDS.includes(command);
  const complaint = command === 'queja'; // SPEC-010 RH13
  const route = {
    kind: booking ? 'booking_command' : complaint ? 'complaint_command' : command || (hasText ? 'text' : 'other'),
    fromId: asId(m.from && m.from.id),
    chatId: m.chat ? m.chat.id : null,
    callbackQueryId: null,
    version: null,
  };
  return booking || complaint ? { ...route, data: command } : route; // SPEC-007: /cita, /micita; SPEC-010: /queja
}

// --- SPEC-010 RH13, RH14: complaint phrases, a strict list (evals/complaint_phrases.yaml) ---
// Works on the pseudonymized text. A match only opens the /queja confirmation; it never posts anything.
function normalizeComplaintText(text) {
  return String(text ?? '')
    .toLowerCase()
    .normalize('NFD').replace(/\p{M}+/gu, '')
    .replace(/\[(nombre|telefono|dni|email)\]/g, ' ')
    .replace(/[^\p{L}\p{N}\s]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
const COMPLAINT_WORDS = /\b(?:queja|quejas|quejar|quejarme|reclamacion|reclamaciones|reclamar)\b/;
// Not a complaint: no complaint, someone else complaining, or an insurance claim.
const COMPLAINT_BLOCKERS = [
  /\b(?:no tengo|sin) (?:ninguna )?quejas?\b/,
  /\bno me quejo\b/,
  /\bse (?:queja|quejan|quejaba|quejo)\b/,
  /\b(?:seguro|aseguradora|reembolso|mutua|tramit\w*)\b/,
];
function detectComplaintPhrase(text) {
  const t = normalizeComplaintText(text);
  return COMPLAINT_WORDS.test(t) && !COMPLAINT_BLOCKERS.some((re) => re.test(t));
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
// SPEC-010: question is the pseudonymized text (for the complaint phrases); handoffAwaiting says whether a
// handoff of this patient waits for the text for reception (from the consent lookup).
function decide({ route, urgency, consent, lookupFailed, question = null, handoffAwaiting = false }) {
  const reply = (text, keyboard) => ({ action: 'reply', text, keyboard });
  const notice = reply(CONSENT_NOTICE, 'consent');
  const inForce = !lookupFailed && isConsentInForce(consent);
  const kind = route && route.kind;

  const urgent = !!(urgency && urgency.urgency_level && urgency.urgency_level !== 'none');
  const handoff = (step, reason, extra = {}) => ({ action: 'handoff', text: null, keyboard: null, step, reason, ...extra });
  if (kind === 'group') throw new Error('decide(): a group update has its own branch (SPEC-010 RH12)');
  if (kind === 'text') {
    // SPEC-010 RH4, RH5: the text a handoff waits for goes to reception (an urgency is answered first).
    if (inForce && handoffAwaiting) return handoff('text', null, { urgent });
    // SPEC-010 RH13–RH15: a complaint phrase opens the /queja confirmation; an urgency always wins.
    if (!urgent && detectComplaintPhrase(question)) {
      if (inForce) return handoff('ask', 'q');
      return reply(COMPLAINT_NO_CONSENT_TEXT, 'none');
    }
    if (inForce) return { action: 'core', text: null, keyboard: null };
    if (urgent) return reply(urgency.text, 'handoff');
    return lookupFailed ? reply(ERROR_TEXT, 'handoff') : notice;
  }
  // SPEC-010 RH1, RH3, RH6, RH7: the handoff steps; «No» needs nothing.
  if (kind === 'handoff_cancel') return handoff('cancel', null);
  if (kind === 'handoff' || kind === 'handoff_confirm') {
    return inForce ? handoff(kind === 'handoff' ? 'ask' : 'confirm', route.reason) : reply(HANDOFF_NO_CONSENT_TEXT, 'none');
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
    case 'complaint_command': // SPEC-010 RH13, RH15
      return inForce ? handoff('ask', 'q') : reply(COMPLAINT_NO_CONSENT_TEXT, 'none');
    case 'rating': // SPEC-010 RH17, RH18
      return inForce ? { action: 'rating', text: null, keyboard: null, value: route.value } : notice;
    case 'unknown_button':
      return notice;
    default:
      throw new Error(`decide(): unknown route kind "${kind}"`);
  }
}
