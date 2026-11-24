// SPEC-010 reception module (specs/011-reception-handoff/spec.md, plan.md Step 1).
// Paste-ready: the n8n Code nodes «Recepción» and «Grupo de recepción» of lifecenter-telegram-demo carry
// this exact code followed only by their wiring. No require, no network, no state: the handoff rows live
// in Neon (007_reception.sql), and no message text is ever stored.

// --- Fixed texts (spec "Fixed texts", verified by the human 2026-11-24) ---
const TEXTS = {
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
// The existing labels and callbacks this module reuses (CHG-001 D8, SPEC-007).
const HANDOFF_LABEL = 'Hablar con recepción';
const BOOKING_LABEL = 'Pedir cita';
const BOOKING_MENU = 'bk:menu';

// --- Reasons (RH2, RH13): the code in the callback, and what reception reads ---
const REASONS = { a: 'abstención', u: 'urgencia', p: 'petición', q: 'queja' };

// --- Codes (P3): R- (handoff) or Q- (complaint) + 4 characters with no look-alikes (no 0, O, 1, I, L).
// The database generates them (unique among open handoffs); this only recognizes them.
const CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
const CODE_PATTERN = /^[RQ]-[ABCDEFGHJKMNPQRSTUVWXYZ2-9]{4}$/;

// --- The reason of «Hablar con recepción» under a reply of B (RH2). B does not change. ---
const ABSTENTION_REASONS = ['below_threshold', 'model_abstained', 'validation_failed'];
function handoffReasonFor(result) {
  const reason = result && result.reason;
  if (reason === 'urgency') return 'u';
  if (ABSTENTION_REASONS.includes(reason)) return 'a';
  return 'p';
}

const fill = (t, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, v), t);

// --- The confirmation (RH1, RH13): «Sí, pasar a recepción» keeps the reason; «No» needs nothing ---
function confirmView(reason) {
  return {
    text: reason === 'q' ? TEXTS.COMPLAINT_CONFIRM : TEXTS.HANDOFF_CONFIRM,
    rows: [[{ text: LABELS.si, data: `hs:${reason}` }], [{ text: LABELS.no, data: 'hn' }]],
  };
}

// --- The message posted in the reception group (RH4, RH5, P4): code, reason, the pseudonymized text,
// and «Cerrar». No name, phone, Telegram user or appointment. An urgency is always marked as one. ---
function groupMessage({ code, reason, text, urgent }) {
  const motivo = REASONS[urgent ? 'u' : reason] || REASONS.p;
  return {
    text: `${fill(TEXTS.GROUP_HEADER, { codigo: code, motivo })}\n\n${text}\n\n${TEXTS.GROUP_FOOTER}`,
    rows: [[{ text: LABELS.cerrar, data: `hc:${code}` }]],
  };
}

// --- What the patient reads (RH4, RH9) ---
const sentText = (code) => fill(TEXTS.HANDOFF_SENT, { codigo: code });
const receptionReply = (code, text) => fill(TEXTS.RECEPTION_REPLY, { codigo: code, texto: text });

// --- An update from a group (RH9–RH12): only a text reply to a bot message, or «Cerrar», in the
// registered reception group. Everything else, from any group, is ignored with no reply. ---
function groupAction(route, receptionChatId) {
  const ignore = { action: 'ignore' };
  if (!route || route.kind !== 'group' || !receptionChatId || String(route.chatId) !== String(receptionChatId)) return ignore;
  if (route.callbackData) {
    const m = /^hc:(.+)$/.exec(route.callbackData);
    return m && CODE_PATTERN.test(m[1])
      ? { action: 'close', code: m[1], callbackQueryId: route.callbackQueryId, messageId: route.messageId } : ignore;
  }
  if (route.replyToMessageId && route.replyToBot && typeof route.text === 'string' && route.text.trim()) {
    return { action: 'forward', replyToMessageId: route.replyToMessageId, text: route.text };
  }
  return ignore;
}

// --- The keyboard under B's replies (RH2, RH16): «Hablar con recepción» with its reason, «Pedir cita»
// (SPEC-007), and 👍/👎 only under an answered reply. ---
function answerRows(result) {
  const rows = [];
  if (result && result.handoff) rows.push([{ text: HANDOFF_LABEL, data: `handoff:${handoffReasonFor(result)}` }]);
  if (result && result.offer_booking === true) rows.push([{ text: BOOKING_LABEL, data: BOOKING_MENU }]);
  if (result && result.reason === 'answered') rows.push([{ text: LABELS.up, data: 'rt:u' }, { text: LABELS.down, data: 'rt:d' }]);
  return rows;
}

// --- The Telegram node's inlineKeyboard parameter, built from the rows (the same shape as citas.js) ---
function toTelegramKeyboard(rows) {
  return {
    rows: rows.map((r) => ({ row: { buttons: r.map((b) => ({ text: b.text, additionalFields: { callback_data: b.data } })) } })),
  };
}
