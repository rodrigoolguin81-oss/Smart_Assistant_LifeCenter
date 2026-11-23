// SPEC-007 booking module (specs/008-booking/spec.md, plan.md Step 1).
// Paste-ready: the n8n Code nodes "¿Es una reserva?", "Preparar reserva" and "Componer reserva" of
// lifecenter-telegram-demo carry this exact code followed only by their wiring (BK23).
// No require, no network, no state: every booking step's state travels in the button (BK12).

// --- Fixed texts (spec "Fixed texts", approved by the human 2026-11-22) ---
const TEXTS = {
  TYPE_MENU: '¿Qué tipo de cita quieres?',
  REQUEST_ONLY: 'Ese tratamiento necesita una valoración previa en la clínica. Puedo reservarte una primera visita, o puedes hablar con recepción.',
  SLOTS: 'Estos son los primeros huecos para {tipo}:',
  // Added by the human at R6 (2026-11-22): the slots after «Ver más».
  MORE_SLOTS: 'Estos son los siguientes huecos para {tipo}:',
  NO_SLOTS: 'Ahora mismo no hay huecos libres para {tipo} en los próximos 30 días. Llama a recepción para buscar otra fecha.',
  CONFIRM: 'Vas a reservar {tipo} el {fecha} a las {hora}. ¿Lo confirmo?',
  // SPEC-008 Q11 (human, 2026-11-23): these three drop «llama a recepción»; the «Cambiar» and
  // «Anular» buttons replace it.
  BOOKED: 'Hecho: tienes {tipo} el {fecha} a las {hora}.',
  TAKEN: 'Ese hueco se acaba de ocupar. Estos son los siguientes:',
  UNAVAILABLE: 'Ese hueco ya no está disponible. Estos son los siguientes:',
  LIMIT: 'Ya tienes {tipo} el {fecha} a las {hora}. Solo se puede tener una cita reservada por el bot.',
  MY_APPOINTMENT: 'Tu próxima cita: {tipo} el {fecha} a las {hora}.',
  NO_APPOINTMENT: 'No tienes ninguna cita reservada. Escribe /cita para pedir una.',
  // Copy of the CHG-001 D7 text, used when a Neon call of a booking step fails (BK20).
  ERROR: 'Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?',
  // --- SPEC-008, moving and cancelling (spec "Fixed texts", human 2026-11-23) ---
  CANCEL_CONFIRM: '¿Seguro que quieres anular {tipo} del {fecha} a las {hora}?',
  CANCELLED: 'Hecho: he anulado {tipo} del {fecha} a las {hora}. Si quieres otra, escribe /cita.',
  CANCELLED_NO_CONSENT: 'Hecho: he anulado {tipo} del {fecha} a las {hora}.',
  MOVE_SLOTS: '¿A cuándo quieres cambiar {tipo} del {fecha} a las {hora}? Estos son los primeros huecos:',
  MOVE_MORE_SLOTS: 'Estos son los siguientes huecos:',
  MOVE_CONFIRM: 'Vas a cambiar {tipo} del {fecha} a las {hora} al {fecha_nueva} a las {hora_nueva}. ¿Lo confirmo?',
  // Changed by the human at the M1 review (2026-11-23): «tu cita», not «una limpieza».
  MOVED: 'Hecho: tu cita pasa al {fecha_nueva} a las {hora_nueva}. La anterior queda anulada.',
  MOVE_TAKEN: 'Ese hueco se acaba de ocupar. Tu cita del {fecha} a las {hora} sigue igual. Estos son los siguientes:',
  MOVE_UNAVAILABLE: 'Ese hueco ya no está disponible. Tu cita del {fecha} a las {hora} sigue igual. Estos son los siguientes:',
  MOVE_NO_SLOTS: 'Ahora mismo no hay otros huecos para {tipo} en los próximos 30 días. Tu cita sigue igual. Llama a recepción para buscar otra fecha.',
  TOO_LATE: 'Tu cita es en menos de {plazo}. Para cambiarla o anularla, llama a recepción.',
  NOT_ACTIVE: 'Esa cita ya no está activa.',
  KEPT: 'De acuerdo, mantengo tu cita.',
  // Appended to the SPEC-006 REVOKED_TEXT (MC11, MC12; the second one: human, spec review).
  // Changed by the human at the M1 review (2026-11-23).
  REVOKED_APPOINTMENT: 'Sigues teniendo {tipo} el {fecha} a las {hora}. Si no vas a ir, puedes anularla aquí o llamar a recepción.',
  REVOKED_LOOKUP_FAILED: 'Si tenías una cita reservada, se mantiene; para anularla, llama a recepción.',
  // --- SPEC-009, reminders (spec "Fixed texts", approved by the human 2026-11-23) ---
  REMINDER_OFFER: '¿Quieres que te recuerde la cita el día antes por aquí?',
  REMINDER_SET: 'De acuerdo, te la recordaré el día antes.',
  REMINDER_OFF: 'De acuerdo, no te enviaré recordatorio.',
  REMINDER_ON_LINE: 'Te recordaré la cita el día antes.',
  ATTENDANCE: 'Gracias, te esperamos.',
  REMINDER_WITHDRAWN: 'No te enviaré recordatorios.',
};

// --- Button labels (approved 2026-11-22) and the existing handoff callback (CHG-001 D8) ---
const LABELS = {
  pedir: 'Pedir cita',
  mas: 'Ver más',
  confirmar: 'Confirmar',
  otroHueco: 'Elegir otro hueco',
  otroTratamiento: 'Otro tratamiento',
  recepcion: 'Hablar con recepción',
  primeraVisita: 'Primera visita',
  // SPEC-008
  cambiar: 'Cambiar',
  anular: 'Anular',
  siAnular: 'Sí, anular',
  mantener: 'Mantener mi cita',
  confirmarCambio: 'Confirmar cambio',
  anularMiCita: 'Anular mi cita',
  // SPEC-009
  siRecuerda: 'Sí, recuérdamela',
  noGracias: 'No, gracias',
  recordarme: 'Recordármela el día antes',
  quitarRecordatorio: 'No quiero recordatorio',
};
const CALLBACK_HANDOFF = 'handoff';

// --- Appointment types: the SPEC-004 codes and names (example data until DEP-03) ---
const TYPE_NAMES = {
  revision: 'Revisión',
  limpieza: 'Limpieza',
  primera_visita: 'Primera visita',
  blanqueamiento: 'Blanqueamiento',
  tratamiento_largo: 'Implantes, ortodoncia u otro tratamiento largo',
};
const BOOKABLE_TYPES = ['revision', 'limpieza', 'primera_visita'];
const REQUEST_ONLY_TYPES = ['blanqueamiento', 'tratamiento_largo'];
// How a bookable type reads inside a sentence («huecos para una limpieza»).
const TYPE_PHRASES = { revision: 'una revisión', limpieza: 'una limpieza', primera_visita: 'una primera visita' };
const typePhrase = (code) => TYPE_PHRASES[code] || String(TYPE_NAMES[code] || code).toLowerCase();

// --- Callback codec (BK12, BK13): every value carries its whole state and fits in 64 bytes ---
// A slot is its start as minutes since the Unix epoch, in base 36.
function encodeSlot(start) {
  return Math.round(new Date(start).getTime() / 60000).toString(36);
}
function decodeSlot(code) {
  if (typeof code !== 'string' || !/^[0-9a-z]{1,8}$/.test(code)) return null;
  return new Date(parseInt(code, 36) * 60000).toISOString();
}
const CALLBACK_PREFIX = { type: 't', slot: 's', confirm: 'c', more: 'm', retry: 'r' };
function cb(kind, type, start) {
  if (kind === 'menu') return 'bk:menu';
  if (kind === 'other') return 'bk:o';
  if (kind === 'type' || kind === 'retry') return `bk:${CALLBACK_PREFIX[kind]}:${type}`;
  return `bk:${CALLBACK_PREFIX[kind]}:${type}:${encodeSlot(start)}`;
}
// SPEC-008 change callbacks (spec "Change callbacks"): no type, because the functions read it from
// the appointment. <start> is always the start of the appointment the button refers to (MC17).
// SPEC-009 adds the reminder callbacks: ry (Sí / Recordármela), rn (No, gracias), rq (No quiero
// recordatorio) and i (Iré), each with the appointment's start.
const CHANGE_PREFIX = {
  keep: 'v', cancel_ask: 'a', cancel: 'ac', move: 'x', move_more: 'xm', move_slot: 'xs', move_confirm: 'xc',
  reminder_on: 'ry', reminder_off: 'rn', reminder_clear: 'rq', attend: 'i',
};
function changeCb(kind, start, other) {
  if (kind === 'view') return 'bk:v';
  const base = `bk:${CHANGE_PREFIX[kind]}:${encodeSlot(start)}`;
  return ['move_more', 'move_slot', 'move_confirm'].includes(kind) ? `${base}:${encodeSlot(other)}` : base;
}
const CHANGE_STEPS = { v: 'keep', a: 'cancel_ask', ac: 'cancel', x: 'move', xm: 'move_more', xs: 'move_slot', xc: 'move_confirm',
  ry: 'reminder_on', rn: 'reminder_off', rq: 'reminder_clear', i: 'attend' };
function parseChangeCallback(data) {
  if (data === 'bk:v') return { step: 'view', type: null, start: null, target: null };
  const m = /^bk:(v|a|ac|x|xm|xs|xc|ry|rn|rq|i):([0-9a-z]+)(?::([0-9a-z]+))?$/.exec(data);
  if (!m) return null;
  const [, p, startCode, otherCode] = m;
  const twoCodes = ['xm', 'xs', 'xc'].includes(p);
  if (twoCodes !== (otherCode !== undefined)) return null;
  const start = decodeSlot(startCode);
  const target = twoCodes ? decodeSlot(otherCode) : null;
  if (!start || (twoCodes && !target)) return null;
  return { step: CHANGE_STEPS[p], type: null, start, target };
}
function parseBookingCallback(data) {
  const bad = { step: 'malformed', type: null, start: null };
  if (data === 'bk:menu') return { step: 'menu', type: null, start: null };
  if (data === 'bk:o') return { step: 'other', type: null, start: null };
  if (typeof data === 'string' && /^bk:(v|a|ac|x|xm|xs|xc|ry|rn|rq|i)(:|$)/.test(data)) return parseChangeCallback(data) || bad;
  const m = /^bk:([tscmr]):([a-z_]+)(?::([0-9a-z]+))?$/.exec(typeof data === 'string' ? data : '');
  if (!m) return bad;
  const [, p, type, slot] = m;
  const step = { t: 'type', s: 'slot', c: 'confirm', m: 'more', r: 'retry' }[p];
  if (!(type in TYPE_NAMES)) return bad;
  if (step === 'type') return slot === undefined ? { step, type, start: null } : bad;
  if (!BOOKABLE_TYPES.includes(type)) return bad; // slots only exist for bookable types
  if (step === 'retry') return slot === undefined ? { step, type, start: null } : bad;
  const start = decodeSlot(slot);
  return start ? { step, type, start } : bad;
}

// --- Booking phrases (BK3, BK4; Decisions Q2): a fixed, strict list ---
// Works on the pseudonymized text: lower case, no accents, placeholders and punctuation removed.
function normalizeText(text) {
  return String(text ?? '')
    .toLowerCase()
    .normalize('NFD').replace(/\p{M}+/gu, '')
    .replace(/\[(nombre|telefono|dni|email)\]/g, ' ')
    .replace(/[^\p{L}\p{N}\s]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
const OBJECT_WORDS = '(?:citas?|hora|huecos?|revision(?:es)?|limpiezas?|primera visita|blanqueamientos?|implantes?|ortodoncia)';
const BOOKING_REQUESTS = [
  new RegExp(`\\b(?:pedir|pido|pida|reservar|reservo|coger|cojo|sacar|saco|concertar|dar|das|dais|dame|darme)\\b.*\\b${OBJECT_WORDS}\\b`),
  /\b(?:quiero|quisiera|querria|necesito|me gustaria)\b.*\b(?:citas?|hora)\b/,
  /\b(?:hay|teneis|tienes|tienen)\b.*\b(?:citas?|huecos?)\b/,
];
// Anything about an existing appointment, prices, moving or cancelling is never a request.
const BOOKING_BLOCKERS = [
  /\b(?:cancelar|cancela|cancelo|anular|anula|anulo|cambiar|cambio|cambiaron|mover|muevo|modificar|aplazar|retrasar|adelantar|olvide|olvido|confirmo|confirmar)\b/,
  /\b(?:mi|mis|tu|tus|su|sus|la|las) citas?\b/,
  /\b(?:tengo|tenia|tenemos|tiene|ya)\b.*\bcitas?\b/,
  /\b(?:cuanto|cuanta|cuesta|cuestan|precio|precios|vale|valen|coste)\b/,
  /\bno (?:quiero|necesito|deseo)\b/,
];
const REQUEST_ONLY_WORDS = /\b(?:blanqueamientos?|blanquear|implantes?|ortodoncia|brackets|endodoncia)\b/;
const TYPE_WORDS = [
  ['primera_visita', /\bprimera visita\b/],
  ['limpieza', /\blimpiezas?\b/],
  ['revision', /\brevision(?:es)?\b/],
];
function detectBookingPhrase(text) {
  const t = normalizeText(text);
  const none = { match: false, type: null, requestOnly: false };
  if (!BOOKING_REQUESTS.some((re) => re.test(t))) return none;
  if (BOOKING_BLOCKERS.some((re) => re.test(t))) return none;
  if (REQUEST_ONLY_WORDS.test(t)) return { match: true, type: null, requestOnly: true };
  const named = TYPE_WORDS.find(([, re]) => re.test(t));
  return { match: true, type: named ? named[0] : null, requestOnly: false };
}
// What "¿Es una reserva?" uses in A (BK2): an urgency always wins, so a message the urgency detector
// flagged is never a booking phrase, whatever it says («quiero cita, me sangra mucho la encía»).
function bookingPhraseFor(question, urgency) {
  if (urgency && urgency.urgency_level && urgency.urgency_level !== 'none') {
    return { match: false, type: null, requestOnly: false };
  }
  return detectBookingPhrase(question);
}

// --- SPEC-008 change and cancel phrases (MC4, MC5): a fixed, strict list ---
// A match only opens the «Mi cita» view: it never cancels or moves, and no date is read from it.
// Verbs in the infinitive or the imperative only: «anuló» normalizes to «anulo», which would also
// match «la clínica me anuló la cita». The object is one's appointment («cita», «hora»), singular.
const CHANGE_VERBS = '(?:cancelar|cancela|anular|anula|cambiar|mover|aplazar|retrasar|adelantar|modificar)';
const CHANGE_REQUESTS = [
  new RegExp(`\\b${CHANGE_VERBS}\\b.*\\b(?:cita|hora)\\b`),
  new RegExp(`\\bcita\\b.*\\b${CHANGE_VERBS}\\b`),
  /\bno (?:puedo|podre|voy a poder) (?:ir|acudir|asistir)\b.*\b(?:cita|hora)\b/,
];
// Policy and price questions, other people's appointments, refusals, and changing the professional
// or the treatment are never a request to change one's own appointment.
const CHANGE_BLOCKERS = [
  /\b(?:cuanto|cuanta|cuesta|cuestan|precio|precios|coste|cobra\w*|penaliza\w*|gratis|multa)\b/,
  /\b(?:madre|padre|hijo|hija|marido|mujer|pareja|hermano|hermana|abuelo|abuela|novio|novia)\b/,
  /\bno (?:quiero|necesito|deseo)\b/,
  /\bcambiar de (?:dentista|odontologo|odontologa|higienista|doctor|doctora|profesional|tratamiento|clinica)\b/,
];
function detectChangePhrase(text) {
  const t = normalizeText(text);
  const match = CHANGE_REQUESTS.some((re) => re.test(t)) && !CHANGE_BLOCKERS.some((re) => re.test(t));
  return { match };
}
// What "¿Es una reserva?" uses in A since SPEC-008 (MC3): an urgency always wins; then a change or
// cancel phrase; then a booking phrase; otherwise the message goes to B.
function textIntentFor(question, urgency) {
  const none = { match: false, intent: null, type: null, requestOnly: false };
  if (urgency && urgency.urgency_level && urgency.urgency_level !== 'none') return none;
  if (detectChangePhrase(question).match) return { match: true, intent: 'change', type: null, requestOnly: false };
  const b = detectBookingPhrase(question);
  return b.match ? { match: true, intent: 'booking', type: b.type, requestOnly: b.requestOnly } : none;
}

// --- Madrid dates (Q15) ---
const WEEKDAYS_SHORT = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
const WEEKDAYS_LONG = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const MONTHS_SHORT = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
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
function shortLabel(value) {
  const p = madridParts(value);
  return `${WEEKDAYS_SHORT[p.weekday]} ${p.d} ${MONTHS_SHORT[p.mo - 1]} · ${hourOf(value)}`;
}
function longDate(value, now) {
  const p = madridParts(value);
  const year = p.y !== madridParts(now).y ? ` de ${p.y}` : '';
  return `${WEEKDAYS_LONG[p.weekday]} ${p.d} de ${MONTHS_LONG[p.mo - 1]}${year}`;
}

// --- What to do for a booking step (BK1, BK5, BK9–BK16, BK18; SPEC-008 MC5–MC18) ---
// route: from "Clasificar" (booking_command / booking_button), or a text with a matching phrase.
// consent: whether consent is in force («Decidir»). Without it, only «Anular», «Sí, anular» and the
// «Mantener mi cita» of the cancel confirmation can get here (SPEC-008 MC10); anything else throws.
// Returns the step and the single query it needs: none | agenda (my next + slots) | book | cancel | move.
function prepare(route, phrase, now, consent = true) {
  const P = (step, query, extra = {}) => ({ step, query, type: null, from: null, start: null, requestOnly: false, ...extra });
  // SPEC-008 steps also carry the target (a new start, or the slot after which «Ver más» goes on) and
  // the consent flag, which compose() needs.
  const PC = (step, query, extra = {}) => P(step, query, { target: null, consent: !!consent, ...extra });
  const nowIso = new Date(now).toISOString();
  const after = (iso) => new Date(Date.parse(iso) + 60000).toISOString();
  const kind = route && route.kind;
  const refuse = () => { throw new Error('prepare(): this step needs consent in force (SPEC-008 MC10)'); };
  if (kind === 'booking_command') {
    if (!consent) refuse();
    if (route.data === 'cita') return P('cita', 'agenda', { from: nowIso });
    if (route.data === 'micita') return P('micita', 'agenda', { from: nowIso });
  }
  if (kind === 'text' && phrase && phrase.match) {
    if (!consent) refuse();
    if (phrase.intent === 'change') return PC('view', 'agenda', { from: nowIso });
    return P('cita', 'agenda', { type: phrase.type || null, from: nowIso, requestOnly: !!phrase.requestOnly });
  }
  if (kind === 'booking_button') {
    const c = parseBookingCallback(route.data);
    if (!consent && !['cancel_ask', 'cancel', 'keep'].includes(c.step)) refuse();
    switch (c.step) {
      case 'menu': return P('cita', 'agenda', { from: nowIso });
      case 'other': return P('request_only', 'none');
      case 'type':
        return REQUEST_ONLY_TYPES.includes(c.type) ? P('request_only', 'none') : P('slots', 'agenda', { type: c.type, from: nowIso });
      case 'slot': return P('confirm', 'none', { type: c.type, start: c.start });
      case 'confirm': return P('book', 'book', { type: c.type, start: c.start });
      case 'more': return P('more', 'agenda', { type: c.type, from: after(c.start) });
      case 'retry': return P('slots', 'agenda', { type: c.type, from: nowIso });
      // SPEC-008
      case 'view': return PC('view', 'agenda', { from: nowIso });
      case 'keep': return consent ? PC('keep', 'agenda', { start: c.start, from: nowIso }) : PC('keep', 'none', { start: c.start });
      case 'cancel_ask': return PC('cancel_confirm', 'agenda', { start: c.start, from: nowIso });
      case 'cancel': return PC('cancel', 'cancel', { start: c.start });
      case 'move': return PC('move_slots', 'agenda', { start: c.start, from: nowIso });
      case 'move_more': return PC('move_more', 'agenda', { start: c.start, from: after(c.target) });
      case 'move_slot': return PC('move_confirm', 'agenda', { start: c.start, target: c.target, from: nowIso });
      case 'move_confirm': return PC('move', 'move', { start: c.start, target: c.target });
      // SPEC-009: the reminder steps (all need consent, RM6). «No, gracias» writes nothing.
      case 'reminder_on': return PC('reminder_on', 'reminder', { start: c.start });
      case 'reminder_off': return PC('reminder_off', 'agenda', { start: c.start, from: nowIso });
      case 'reminder_clear': return PC('reminder_clear', 'reminder', { start: c.start });
      case 'attend': return PC('attend', 'reminder', { start: c.start });
      default: return P('menu', 'none');
    }
  }
  throw new Error(`prepare(): not a booking step (${kind})`);
}

// --- Shared text helpers ---
const fillText = (t, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, v), t);
// SPEC-008 MC19: {plazo} of TOO_LATE_TEXT, from change_min_lead in minutes («2 horas»).
function plazoText(minutes) {
  if (minutes % 60 === 0) return minutes === 60 ? '1 hora' : `${minutes / 60} horas`;
  return `${minutes} minutos`;
}
// The example value of change_min_lead (SPEC-008 MC19), used only if a query did not return it.
const DEFAULT_CHANGE_MIN_MINUTES = 120;
// SPEC-009 Q7, RM1: the reminder is offered only for an appointment at least 3 hours away.
const REMINDER_OPT_IN_MINUTES = 180;

// --- Text and keyboard rows for every result (BK9–BK20; SPEC-008 MC1–MC18, MC24) ---
// db: { failed } | { agenda: { my_next, slots, change_min_minutes } }
//   | { book: { result, reason, starts_at, next_slots, my_next } }
//   | { cancel: { result, type_code, starts_at, ends_at, my_next, change_min_minutes } }
//   | { move: { result, reason, type_code, old_starts_at, old_ends_at, starts_at, ends_at, next_slots, my_next,
//               change_min_minutes } }
//   | { reminder: { result, my_next, has_reminder, change_min_minutes } }   (SPEC-009)
// has_reminder: whether the current appointment has a reminder. When a query does not say (undefined),
// the view shows no reminder line or button.
function compose(prep, db, now) {
  const button = (text, data) => ({ text, data });
  const reception = [button(LABELS.recepcion, CALLBACK_HANDOFF)];
  const fill = fillText;
  const when = (start) => ({ fecha: longDate(start, now), hora: hourOf(start) });
  const view = (text, rows) => ({ text, rows });
  const consent = prep.consent !== false;
  const menu = () => view(TEXTS.TYPE_MENU, [
    ...BOOKABLE_TYPES.map((t) => [button(TYPE_NAMES[t], cb('type', t))]),
    [button(LABELS.otroTratamiento, cb('other'))],
    reception,
  ]);
  const requestOnly = () => view(TEXTS.REQUEST_ONLY, [[button(LABELS.primeraVisita, cb('type', 'primera_visita'))], reception]);
  // SPEC-008 MC1: every message that shows the current appointment offers to change or cancel it.
  const changeRows = (start) => [
    [button(LABELS.cambiar, changeCb('move', start))],
    [button(LABELS.anular, changeCb('cancel_ask', start))],
    reception,
  ];
  // my: agenda_my_next's row { type_code, starts_at, ends_at } (spec BK19)
  const appointment = (text, my) => view(fill(text, { tipo: typePhrase(my.type_code), ...when(my.starts_at) }), changeRows(my.starts_at));
  const slotList = (text, type, slots) => {
    if (!slots || !slots.length) return view(fill(TEXTS.NO_SLOTS, { tipo: typePhrase(type) }), [reception]);
    return view(fill(text, { tipo: typePhrase(type) }), [
      ...slots.map((s) => [button(shortLabel(s.starts_at), cb('slot', type, s.starts_at))]),
      [button(LABELS.mas, cb('more', type, slots[slots.length - 1].starts_at))],
      reception,
    ]);
  };
  // --- SPEC-008 helpers ---
  const sameStart = (a, b) => !!a && !!b && Date.parse(a) === Date.parse(b);
  const minutesOf = (x) => (x && Number.isFinite(x.change_min_minutes) ? x.change_min_minutes : DEFAULT_CHANGE_MIN_MINUTES);
  // SPEC-009 RM1, RM5: the opt-in window, and the view's reminder line and button.
  const inOptIn = (start) => Date.parse(start) >= Date.parse(now) + REMINDER_OPT_IN_MINUTES * 60000;
  const myView = (my, hasReminder) => {
    if (!my) return view(TEXTS.NO_APPOINTMENT, [[button(LABELS.pedir, cb('menu'))], reception]);
    const base = appointment(TEXTS.MY_APPOINTMENT, my);
    if (typeof hasReminder !== 'boolean' || !inOptIn(my.starts_at)) return base;
    return view(hasReminder ? `${base.text}
${TEXTS.REMINDER_ON_LINE}` : base.text, [
      [button(LABELS.cambiar, changeCb('move', my.starts_at))],
      [button(LABELS.anular, changeCb('cancel_ask', my.starts_at))],
      [hasReminder ? button(LABELS.quitarRecordatorio, changeCb('reminder_clear', my.starts_at))
        : button(LABELS.recordarme, changeCb('reminder_on', my.starts_at))],
      reception,
    ]);
  };
  const prefixed = (prefix, v) => view(`${prefix}\n\n${v.text}`, v.rows);
  // Without consent (MC10), a step shows only what concerns that appointment.
  const notActive = (my, hasReminder) => (consent ? prefixed(TEXTS.NOT_ACTIVE, myView(my, hasReminder)) : view(TEXTS.NOT_ACTIVE, [reception]));
  const tooLate = (minutes) => view(fill(TEXTS.TOO_LATE, { plazo: plazoText(minutes) }), [reception]);
  // The appointment at the button's start must still be the current one, and not too close (MC17, MC18).
  const checkCurrent = (agenda) => {
    const my = agenda.my_next;
    if (!my || !sameStart(my.starts_at, prep.start)) return { stop: notActive(my, agenda.has_reminder) };
    if (Date.parse(my.starts_at) < Date.parse(now) + minutesOf(agenda) * 60000) return { stop: tooLate(minutesOf(agenda)) };
    return { my };
  };
  // The slots for a move: never the current start; then «Ver más», «Mantener mi cita», reception.
  const moveList = (text, type, start, slots) => {
    const others = (slots || []).filter((s) => !sameStart(s.starts_at, start));
    if (!others.length) return view(fill(TEXTS.MOVE_NO_SLOTS, { tipo: typePhrase(type) }), [reception]);
    return view(text, [
      ...others.map((s) => [button(shortLabel(s.starts_at), changeCb('move_slot', start, s.starts_at))]),
      [button(LABELS.mas, changeCb('move_more', start, others[others.length - 1].starts_at))],
      [button(LABELS.mantener, changeCb('view'))],
      reception,
    ]);
  };

  if (db && db.failed) return view(TEXTS.ERROR, [reception]);
  const agenda = (db && db.agenda) || {};
  switch (prep.step) {
    case 'micita':
      return myView(agenda.my_next, agenda.has_reminder);
    case 'cita':
      if (agenda.my_next) return appointment(TEXTS.LIMIT, agenda.my_next);
      if (prep.requestOnly) return requestOnly();
      if (prep.type) return slotList(TEXTS.SLOTS, prep.type, agenda.slots);
      return menu();
    case 'slots':
    case 'more':
      if (agenda.my_next) return appointment(TEXTS.LIMIT, agenda.my_next);
      return slotList(prep.step === 'more' ? TEXTS.MORE_SLOTS : TEXTS.SLOTS, prep.type, agenda.slots);
    case 'request_only':
      return requestOnly();
    case 'menu':
      return menu();
    case 'confirm':
      return view(fill(TEXTS.CONFIRM, { tipo: typePhrase(prep.type), ...when(prep.start) }), [
        [button(LABELS.confirmar, cb('confirm', prep.type, prep.start))],
        [button(LABELS.otroHueco, cb('retry', prep.type))],
      ]);
    case 'book': {
      const b = (db && db.book) || {};
      if (b.result === 'booked') {
        const booked = fill(TEXTS.BOOKED, { tipo: typePhrase(prep.type), ...when(b.starts_at) });
        if (!inOptIn(b.starts_at)) return view(booked, changeRows(b.starts_at));
        // SPEC-009 RM1: the reminder offer, in the same message (5 rows).
        return view(`${booked}

${TEXTS.REMINDER_OFFER}`, [
          [button(LABELS.siRecuerda, changeCb('reminder_on', b.starts_at))],
          [button(LABELS.noGracias, changeCb('reminder_off', b.starts_at))],
          ...changeRows(b.starts_at),
        ]);
      }
      if (b.result === 'limit' && b.my_next) return appointment(TEXTS.LIMIT, b.my_next);
      if (b.result === 'taken') return slotList(TEXTS.TAKEN, prep.type, b.next_slots);
      if (b.result === 'invalid' && ['request_only', 'unknown_type'].includes(b.reason)) return menu();
      if (b.result === 'invalid') return slotList(TEXTS.UNAVAILABLE, prep.type, b.next_slots);
      return view(TEXTS.ERROR, [reception]); // an unexpected result is reported as a failure
    }
    // --- SPEC-008 ---
    case 'view':
      return myView(agenda.my_next, agenda.has_reminder);
    case 'keep':
      return consent ? prefixed(TEXTS.KEPT, myView(agenda.my_next, agenda.has_reminder)) : view(TEXTS.KEPT, [reception]);
    case 'cancel_confirm': {
      const c = checkCurrent(agenda);
      if (c.stop) return c.stop;
      return view(fill(TEXTS.CANCEL_CONFIRM, { tipo: typePhrase(c.my.type_code), ...when(c.my.starts_at) }), [
        [button(LABELS.siAnular, changeCb('cancel', prep.start))],
        [button(LABELS.mantener, changeCb('keep', prep.start))],
      ]);
    }
    case 'cancel': {
      const x = (db && db.cancel) || {};
      if (x.result === 'cancelled') {
        const vars = { tipo: typePhrase(x.type_code), ...when(x.starts_at) };
        return consent ? view(fill(TEXTS.CANCELLED, vars), [[button(LABELS.pedir, cb('menu'))], reception])
          : view(fill(TEXTS.CANCELLED_NO_CONSENT, vars), [reception]);
      }
      if (x.result === 'too_late') return tooLate(minutesOf(x));
      if (x.result === 'not_found') return notActive(x.my_next, x.has_reminder);
      return view(TEXTS.ERROR, [reception]);
    }
    case 'move_slots':
    case 'move_more': {
      const c = checkCurrent(agenda);
      if (c.stop) return c.stop;
      const text = prep.step === 'move_slots'
        ? fill(TEXTS.MOVE_SLOTS, { tipo: typePhrase(c.my.type_code), ...when(c.my.starts_at) }) : TEXTS.MOVE_MORE_SLOTS;
      return moveList(text, c.my.type_code, prep.start, agenda.slots);
    }
    case 'move_confirm': {
      const c = checkCurrent(agenda);
      if (c.stop) return c.stop;
      return view(fill(TEXTS.MOVE_CONFIRM, {
        tipo: typePhrase(c.my.type_code), ...when(c.my.starts_at),
        fecha_nueva: longDate(prep.target, now), hora_nueva: hourOf(prep.target),
      }), [
        [button(LABELS.confirmarCambio, changeCb('move_confirm', prep.start, prep.target))],
        [button(LABELS.otroHueco, changeCb('move', prep.start))],
        [button(LABELS.mantener, changeCb('view'))],
      ]);
    }
    case 'move': {
      const m = (db && db.move) || {};
      if (m.result === 'moved') {
        return view(fill(TEXTS.MOVED, { tipo: typePhrase(m.type_code), fecha_nueva: longDate(m.starts_at, now), hora_nueva: hourOf(m.starts_at) }),
          changeRows(m.starts_at));
      }
      if (m.result === 'taken' || m.result === 'invalid') {
        const text = fill(m.result === 'taken' ? TEXTS.MOVE_TAKEN : TEXTS.MOVE_UNAVAILABLE, when(m.old_starts_at));
        return moveList(text, m.type_code, prep.start, m.next_slots);
      }
      if (m.result === 'too_late') return tooLate(minutesOf(m));
      if (m.result === 'not_found') return notActive(m.my_next, m.has_reminder);
      return view(TEXTS.ERROR, [reception]);
    }
    // --- SPEC-009 ---
    case 'reminder_on': {
      const r = (db && db.reminder) || {};
      if (r.result === 'set') return prefixed(TEXTS.REMINDER_SET, myView(r.my_next, r.has_reminder));
      if (r.result === 'too_late') return myView(r.my_next, r.has_reminder); // under 3 h: no reminder button
      if (r.result === 'not_found') return notActive(r.my_next, r.has_reminder);
      return view(TEXTS.ERROR, [reception]);
    }
    case 'reminder_off':
      return prefixed(TEXTS.REMINDER_OFF, myView(agenda.my_next, agenda.has_reminder));
    case 'reminder_clear': {
      const r = (db && db.reminder) || {};
      if (r.result === 'cleared') return prefixed(TEXTS.REMINDER_OFF, myView(r.my_next, r.has_reminder));
      if (r.result === 'not_found') return notActive(r.my_next, r.has_reminder);
      return view(TEXTS.ERROR, [reception]);
    }
    case 'attend': {
      const r = (db && db.reminder) || {};
      if (r.result === 'confirmed' || r.result === 'already') return view(TEXTS.ATTENDANCE, changeRows(prep.start));
      if (r.result === 'not_found') return notActive(r.my_next, r.has_reminder);
      return view(TEXTS.ERROR, [reception]);
    }
    default:
      throw new Error(`compose(): unknown step ${prep.step}`);
  }
}

// --- SPEC-008 MC11, MC12: the reply to a withdrawal («Componer retirada») ---
// revokedText: the SPEC-006 REVOKED_TEXT from «Decidir»; myNext: agenda_my_next's row, or null;
// lookupFailed: the appointment lookup after the withdrawal failed. The withdrawal stands either way.
// SPEC-009 RM12: hadReminder adds «No te enviaré recordatorios.» (the reminder was deleted with the withdrawal).
function revokedReply(revokedText, myNext, lookupFailed, now, hadReminder = false) {
  if (lookupFailed) return { text: `${revokedText}\n\n${TEXTS.REVOKED_LOOKUP_FAILED}`, rows: [] };
  const tail = hadReminder ? `\n\n${TEXTS.REMINDER_WITHDRAWN}` : '';
  if (!myNext) return { text: `${revokedText}${tail}`, rows: [] };
  const line = fillText(TEXTS.REVOKED_APPOINTMENT, {
    tipo: typePhrase(myNext.type_code), fecha: longDate(myNext.starts_at, now), hora: hourOf(myNext.starts_at),
  });
  return {
    text: `${revokedText}\n\n${line}${tail}`,
    rows: [[{ text: LABELS.anularMiCita, data: changeCb('cancel_ask', myNext.starts_at) }]],
  };
}

// --- The Telegram node's inlineKeyboard parameter, built from the rows (plan Step 5) ---
function toTelegramKeyboard(rows) {
  return {
    rows: rows.map((r) => ({ row: { buttons: r.map((b) => ({ text: b.text, additionalFields: { callback_data: b.data } })) } })),
  };
}
