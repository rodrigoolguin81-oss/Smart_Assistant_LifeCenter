// SPEC-007 booking module (specs/008-booking/spec.md, plan.md Step 1).
// Paste-ready: the n8n Code nodes "¿Es una reserva?", "Preparar reserva" and "Componer reserva" of
// lifecenter-telegram-demo carry this exact code followed only by their wiring (BK23).
// No require, no network, no state: every booking step's state travels in the button (BK12).

// --- Fixed texts (spec "Fixed texts", approved by the human 2026-11-22) ---
const TEXTS = {
  TYPE_MENU: '¿Qué tipo de cita quieres?',
  REQUEST_ONLY: 'Ese tratamiento necesita una valoración previa en la clínica. Puedo reservarte una primera visita, o puedes hablar con recepción.',
  SLOTS: 'Estos son los primeros huecos para {tipo}:',
  NO_SLOTS: 'Ahora mismo no hay huecos libres para {tipo} en los próximos 30 días. Llama a recepción para buscar otra fecha.',
  CONFIRM: 'Vas a reservar {tipo} el {fecha} a las {hora}. ¿Lo confirmo?',
  BOOKED: 'Hecho: tienes {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, de momento llama a recepción.',
  TAKEN: 'Ese hueco se acaba de ocupar. Estos son los siguientes:',
  UNAVAILABLE: 'Ese hueco ya no está disponible. Estos son los siguientes:',
  // Changed by the human at R1 review (2026-11-22): «Ya tienes una limpieza el …».
  LIMIT: 'Ya tienes {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, llama a recepción.',
  MY_APPOINTMENT: 'Tu próxima cita: {tipo} el {fecha} a las {hora}. Para cambiarla o anularla, llama a recepción.',
  NO_APPOINTMENT: 'No tienes ninguna cita reservada. Escribe /cita para pedir una.',
  // Copy of the CHG-001 D7 text, used when a Neon call of a booking step fails (BK20).
  ERROR: 'Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?',
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
function parseBookingCallback(data) {
  const bad = { step: 'malformed', type: null, start: null };
  if (data === 'bk:menu') return { step: 'menu', type: null, start: null };
  if (data === 'bk:o') return { step: 'other', type: null, start: null };
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

// --- What to do for a booking step (BK1, BK5, BK9–BK16, BK18) ---
// route: from "Clasificar" (booking_command / booking_button), or a text with a matching phrase.
// Returns the step and the single query it needs: none | agenda (my next + slots) | book.
function prepare(route, phrase, now) {
  const P = (step, query, extra = {}) => ({ step, query, type: null, from: null, start: null, requestOnly: false, ...extra });
  const nowIso = new Date(now).toISOString();
  const kind = route && route.kind;
  if (kind === 'booking_command') {
    if (route.data === 'cita') return P('cita', 'agenda', { from: nowIso });
    if (route.data === 'micita') return P('micita', 'agenda', { from: nowIso });
  }
  if (kind === 'text' && phrase && phrase.match) {
    return P('cita', 'agenda', { type: phrase.type || null, from: nowIso, requestOnly: !!phrase.requestOnly });
  }
  if (kind === 'booking_button') {
    const c = parseBookingCallback(route.data);
    switch (c.step) {
      case 'menu': return P('cita', 'agenda', { from: nowIso });
      case 'other': return P('request_only', 'none');
      case 'type':
        return REQUEST_ONLY_TYPES.includes(c.type) ? P('request_only', 'none') : P('slots', 'agenda', { type: c.type, from: nowIso });
      case 'slot': return P('confirm', 'none', { type: c.type, start: c.start });
      case 'confirm': return P('book', 'book', { type: c.type, start: c.start });
      case 'more': return P('slots', 'agenda', { type: c.type, from: new Date(Date.parse(c.start) + 60000).toISOString() });
      case 'retry': return P('slots', 'agenda', { type: c.type, from: nowIso });
      default: return P('menu', 'none');
    }
  }
  throw new Error(`prepare(): not a booking step (${kind})`);
}

// --- Text and keyboard rows for every result (BK9–BK20) ---
// db: { failed } | { agenda: { my_next, slots } } | { book: { result, reason, starts_at, next_slots, my_next } }
function compose(prep, db, now) {
  const button = (text, data) => ({ text, data });
  const reception = [button(LABELS.recepcion, CALLBACK_HANDOFF)];
  const fill = (t, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, v), t);
  const when = (start) => ({ fecha: longDate(start, now), hora: hourOf(start) });
  const view = (text, rows) => ({ text, rows });
  const menu = () => view(TEXTS.TYPE_MENU, [
    ...BOOKABLE_TYPES.map((t) => [button(TYPE_NAMES[t], cb('type', t))]),
    [button(LABELS.otroTratamiento, cb('other'))],
    reception,
  ]);
  const requestOnly = () => view(TEXTS.REQUEST_ONLY, [[button(LABELS.primeraVisita, cb('type', 'primera_visita'))], reception]);
  // my: agenda_my_next's row { type_code, starts_at, ends_at } (spec BK19)
  const appointment = (text, my) => view(fill(text, { tipo: typePhrase(my.type_code), ...when(my.starts_at) }), [reception]);
  const slotList = (text, type, slots) => {
    if (!slots || !slots.length) return view(fill(TEXTS.NO_SLOTS, { tipo: typePhrase(type) }), [reception]);
    return view(fill(text, { tipo: typePhrase(type) }), [
      ...slots.map((s) => [button(shortLabel(s.starts_at), cb('slot', type, s.starts_at))]),
      [button(LABELS.mas, cb('more', type, slots[slots.length - 1].starts_at))],
      reception,
    ]);
  };

  if (db && db.failed) return view(TEXTS.ERROR, [reception]);
  const agenda = (db && db.agenda) || {};
  switch (prep.step) {
    case 'micita':
      return agenda.my_next ? appointment(TEXTS.MY_APPOINTMENT, agenda.my_next)
        : view(TEXTS.NO_APPOINTMENT, [[button(LABELS.pedir, cb('menu'))], reception]);
    case 'cita':
      if (agenda.my_next) return appointment(TEXTS.LIMIT, agenda.my_next);
      if (prep.requestOnly) return requestOnly();
      if (prep.type) return slotList(TEXTS.SLOTS, prep.type, agenda.slots);
      return menu();
    case 'slots':
      if (agenda.my_next) return appointment(TEXTS.LIMIT, agenda.my_next);
      return slotList(TEXTS.SLOTS, prep.type, agenda.slots);
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
      if (b.result === 'booked') return view(fill(TEXTS.BOOKED, { tipo: typePhrase(prep.type), ...when(b.starts_at) }), [reception]);
      if (b.result === 'limit' && b.my_next) return appointment(TEXTS.LIMIT, b.my_next);
      if (b.result === 'taken') return slotList(TEXTS.TAKEN, prep.type, b.next_slots);
      if (b.result === 'invalid' && ['request_only', 'unknown_type'].includes(b.reason)) return menu();
      if (b.result === 'invalid') return slotList(TEXTS.UNAVAILABLE, prep.type, b.next_slots);
      return view(TEXTS.ERROR, [reception]); // an unexpected result is reported as a failure
    }
    default:
      throw new Error(`compose(): unknown step ${prep.step}`);
  }
}

// --- The Telegram node's inlineKeyboard parameter, built from the rows (plan Step 5) ---
function toTelegramKeyboard(rows) {
  return {
    rows: rows.map((r) => ({ row: { buttons: r.map((b) => ({ text: b.text, additionalFields: { callback_data: b.data } })) } })),
  };
}
