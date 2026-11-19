// SPEC-003 urgency detector (specs/004-urgencies/plan.md). Deterministic: no LLM, no network.
// Paste-ready for the n8n Code node "Detectar urgencia": no require/module/export here; the node
// appends only its input/output wiring (U16). Tested by n8n/code/urgencias.test.js.

// --- Configuration (U13) — the clinic's urgency phone. Example value until DEP-01. ---
const URGENCY_PHONE = '000 000 000';
const URGENCY_PHONE_IS_EXAMPLE = true;

// --- Fixed texts (spec "Fixed texts"; approved by the human 2026-11-19; pending clinical review) ---
const URGENT_MESSAGE =
  `No puedo valorar síntomas por aquí. Llama a la clínica al ${URGENCY_PHONE}. ` +
  'Si es grave o tienes dificultad para respirar, llama al 112.';
const SEVERE_MESSAGE =
  'Si tienes dificultad para respirar o tragar, una hemorragia que no para o te has dado un golpe ' +
  'fuerte en la cara o la cabeza, llama ahora al 112. No puedo valorar síntomas por aquí. ' +
  `Si no es una emergencia, llama a la clínica al ${URGENCY_PHONE}.`;
const EXAMPLE_PHONE_NOTICE =
  '(Este teléfono es de ejemplo: todavía no tenemos el número real de la clínica.)';

// --- Question flag and normalization (U10) ---
// The flag is read on the raw (pseudonymized) text, before normalize() removes punctuation.
function isQuestion(text) {
  return /[¿?]/.test(String(text ?? ''));
}

// Lowercase, no accents, SPEC-001 placeholders removed, punctuation removed, single spaces.
function normalize(text) {
  return String(text ?? '')
    .toLowerCase()
    .normalize('NFD').replace(/\p{M}+/gu, '')
    .replace(/\[(nombre|telefono|dni|email)\]/g, ' ')
    .replace(/[^\p{L}\p{N}\s]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// --- Rule tables (provisional clinical criteria, clarifications A1/A3; pending Prince Calderon).
// Every pattern works on normalize()d text. A rule with several patterns needs all of them. ---
const SWELLING = /\b(hinch\w*|inflam\w*)\b/;
const BLEEDING = /\bsangr\w*/;
const BLOW = /\b(golpe\w*|caida|me cai|me he caido|se ha caido|accidente|traumatismo)\b/;

// Removed from the text before classifying (U8).
const FIGURATIVE = [
  { id: 'fig_duele_que', re: /\b(?:me |te |nos )?duele (?:pensar|pagar|gastar|tener que|que|ver|saber|el bolsillo|la cartera)\b/g },
  { id: 'fig_de_golpe', re: /\bde golpe\b/g },
  { id: 'fig_me_muero_de', re: /\bme muero de (?:ganas|risa)\b/g },
];

// A1 — severe signs.
const SEVERE_RULES = [
  { id: 'sev_breath_swallow', all: [/\b(?:no puedo|me cuesta|le cuesta|dificultad para|no consigo|no puede)(?: \w+)? (?:respirar|tragar)\b/] },
  { id: 'sev_swelling_neck_eye', all: [SWELLING, /\b(?:cuello|ojo|ojos|no puedo abrir)\b/] },
  { id: 'sev_bleeding_nonstop', all: [BLEEDING, /\b(?:no para|no se para|no deja de|sin parar|no se corta|a chorro)\b/] },
  { id: 'sev_blow_face_head', all: [BLOW, /\b(?:cara|cabeza|mandibula)\b/] },
  { id: 'sev_blow_unconscious', all: [BLOW, /\b(?:desmay\w*|conocimiento|inconsciente)\b/] },
  { id: 'sev_blow_tooth_out', all: [BLOW, /\b(?:se me ha caido|se le ha caido|arrancado)(?: \w+)? (?:un |el )?(?:diente|muela)\b/] },
  { id: 'sev_fever_swelling', all: [/\bfiebre\b/, SWELLING] },
];

// A3 — symptom terms.
const SYMPTOM_TERMS = [
  { id: 'sym_pain', all: [/\b(?:dolor\w*|duele|duelen|doler|dolera|doloros\w*|molest\w*|pinchazo\w*)\b/] },
  { id: 'sym_bleeding', all: [BLEEDING] },
  { id: 'sym_swelling', all: [SWELLING] },
  { id: 'sym_fever', all: [/\bfiebre\b/] },
  { id: 'sym_infection', all: [/\b(?:pus|absces\w*|flemon\w*|infecc\w*)\b/] },
  { id: 'sym_blow', all: [/\b(?:golpe\w*|traumatismo)\b/] },
  { id: 'sym_tooth_damage', all: [
    /\b(?:diente|dientes|muela|muelas|corona|empaste|funda|puente)\b/,
    /\b(?:roto|rota|partido|partida|caido|caida|se mueve|se me mueve|suelto|suelta|flojo|floja|movido)\b/,
  ] },
];

// Hypothetical forms about a treatment: they take precedence over "me" (plan, step 4).
const HYPOTHETICAL = [
  /\b(?:me |te )?(?:va|van) a doler\b/g,
  /\bdolera\b/g,
  /\bes doloros[oa]\b/g,
  /\bduele mucho (?:la|el)\b/g,
];

// Signs that the patient reports an own, current or recent state.
const PERSONAL_MARKERS = [
  /\bme (?:duele\w*|sangr\w*|molest\w*|hinch\w*|ha|he|han|esta\w*|noto|sale|cuesta|di|hicieron|pusieron)\b/,
  /\bmis?\b/,
  /\b(?:tengo|tiene|estoy|llevo|lleva|noto|sigue)\b/,
  /\bse (?:me|le)\b/,
  /\bdesde (?:ayer|hace|esta|el|que)\b/,
  /\b(?:hoy|anoche|ahora)\b/,
];

const TREATMENT_WORDS =
  /\b(?:limpieza|blanqueamiento|ortodoncia|implantes?|endodoncia|extraccion|empastes?|tratamiento|anestesia|revision|radiografia|brackets)\b/;

function firing(rules, text) {
  return rules.filter((r) => r.all.every((re) => re.test(text))).map((r) => r.id);
}

// --- Classification (U5–U9) ---
function detectUrgency(text) {
  const question = isQuestion(text);
  let t = normalize(text);
  const matched = [];

  for (const f of FIGURATIVE) {
    if (f.re.test(t)) {
      matched.push(f.id);
      f.re.lastIndex = 0;
      t = t.replace(f.re, ' ').replace(/\s+/g, ' ').trim();
    }
    f.re.lastIndex = 0;
  }

  const severe = firing(SEVERE_RULES, t);
  if (severe.length) return { level: 'severe', matched: matched.concat(severe), question };

  const symptoms = firing(SYMPTOM_TERMS, t);
  if (!symptoms.length) return { level: 'none', matched, question };
  matched.push(...symptoms);

  let withoutHypothetical = t;
  let hypothetical = false;
  for (const re of HYPOTHETICAL) {
    re.lastIndex = 0;
    if (re.test(withoutHypothetical)) {
      hypothetical = true;
      re.lastIndex = 0;
      withoutHypothetical = withoutHypothetical.replace(re, ' ');
    }
    re.lastIndex = 0;
  }
  const personal = PERSONAL_MARKERS.some((re) => re.test(withoutHypothetical));
  if (!personal && TREATMENT_WORDS.test(t) && (question || hypothetical)) {
    matched.push(hypothetical ? 'info_hypothetical' : 'info_question');
    return { level: 'none', matched, question };
  }

  matched.push(personal ? 'reported_state' : 'doubt');
  return { level: 'urgent', matched, question };
}

// --- Reply (U11–U13): fixed text only, built from the level, never from the message. ---
function composeUrgencyReply(level) {
  const base = level === 'severe' ? SEVERE_MESSAGE : URGENT_MESSAGE;
  return URGENCY_PHONE_IS_EXAMPLE ? `${base}\n\n${EXAMPLE_PHONE_NOTICE}` : base;
}
