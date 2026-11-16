"""Pseudonymize a patient's question before it leaves the application (R4, R5; PRD RES-02).

Regex + heuristics, no NLP dependency (clarifications Q5):
- emails → [EMAIL]; DNI/NIE → [DNI]; Spanish phone numbers → [TELEFONO];
- names introduced by "me llamo", "mi nombre es" or "a nombre de" → [NOMBRE].

"soy X" is deliberately NOT a name pattern: in Spanish it usually introduces conditions the
assistant needs ("soy alérgica a la anestesia"). Known limitation: a bare name with no
introduction is not detected.
"""

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
NIE = re.compile(r"(?<!\w)[XYZxyz][\s-]?\d{7}[\s-]?[A-Za-z](?!\w)")
DNI = re.compile(r"(?<!\w)\d{8}[\s-]?[A-Za-z](?!\w)")
# Optional +34 / 0034 prefix, then 9 digits starting with 6, 7, 8 or 9, grouped by
# optional spaces, dots or dashes.
PHONE = re.compile(r"(?<![\w+])(?:(?:\+|00)34[\s.-]?)?[6789]\d{2}(?:[\s.-]?\d){6}(?!\w)")

NAME_INTRO = re.compile(r"(?i:\b(?:me\s+llamo|mi\s+nombre\s+es|a\s+nombre\s+de))\s+")
WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
SPACES = re.compile(r"\s+")

NAME_CONNECTORS = frozenset({"de", "del", "la", "las", "los"})
MAX_NAME_WORDS = 4
# Lowercase path: a second lowercase word is taken as a surname unless it is one of these.
NOT_A_SURNAME = frozenset(
    {
        "y", "e", "o", "u", "que", "quiero", "quisiera", "querría", "para", "por", "con", "sin",
        "de", "del", "la", "el", "los", "las", "un", "una", "tengo", "necesito", "me", "mi",
        "a", "al", "en", "es", "soy", "pero", "porque", "gracias", "hola", "buenas", "buenos",
        "cuánto", "cuanto", "cómo", "como", "qué", "cuándo", "cuando", "pido", "pedir",
    }
)


def pseudonymize(text: str) -> str:
    """Return `text` with direct identifiers replaced by placeholders; everything else intact."""
    text = EMAIL.sub("[EMAIL]", text)
    text = NIE.sub("[DNI]", text)
    text = DNI.sub("[DNI]", text)
    text = PHONE.sub("[TELEFONO]", text)
    return _replace_names(text)


def _replace_names(text: str) -> str:
    out: list[str] = []
    pos = 0
    for intro in NAME_INTRO.finditer(text):
        if intro.start() < pos:  # inside a name already replaced
            continue
        end = _name_end(text, intro.end())
        if end is None:
            continue
        out.append(text[pos:intro.end()])
        out.append("[NOMBRE]")
        pos = end
    out.append(text[pos:])
    return "".join(out)


def _name_end(text: str, start: int) -> int | None:
    """End offset of the name starting at `start`, or None if no name follows."""
    first = WORD.match(text, start)
    if not first:
        return None
    if first.group()[0].isupper():
        return _capitalized_name_end(text, first)
    return _lowercase_name_end(text, first)


def _capitalized_name_end(text: str, first: re.Match) -> int:
    """'Ana García', 'María de la Fuente López': capitalized words, joined by connectors."""
    end, words, cursor = first.end(), 1, first.end()
    while words < MAX_NAME_WORDS:
        connectors_end = cursor
        while True:
            gap = SPACES.match(text, connectors_end)
            word = WORD.match(text, gap.end()) if gap else None
            if word and word.group().lower() in NAME_CONNECTORS:
                connectors_end = word.end()
                continue
            break
        if not word or not word.group()[0].isupper():
            break
        end = cursor = word.end()
        words += 1
    return end


def _lowercase_name_end(text: str, first: re.Match) -> int | None:
    """'ana garcía y quiero…': the first word, plus one more unless it is a common word."""
    if first.group().lower() in NOT_A_SURNAME:
        return None  # not a name (e.g. "a nombre de mi hija"): leave the text intact
    gap = SPACES.match(text, first.end())
    second = WORD.match(text, gap.end()) if gap else None
    if second and second.group().islower() and second.group() not in NOT_A_SURNAME:
        return second.end()
    return first.end()
