"""Knowledge base document schema (R1, R10): Markdown with YAML frontmatter. Pure — no I/O.

Validation errors are written in plain Spanish and name the offending file, since whoever
maintains `kb/` is not necessarily technical.
"""

import re
from dataclasses import dataclass
from datetime import date

import yaml

REQUIRED_FIELDS = ("id", "tipo", "titulo", "vigente_desde")

SECTION_HEADING = re.compile(r"^## ", re.MULTILINE)
"""Start of a level-2 Markdown section: the chunking unit (R2)."""


class InvalidKbDocument(ValueError):
    """A `kb/*.md` document does not satisfy the frontmatter schema."""


@dataclass(frozen=True)
class KbDocument:
    """A validated knowledge base document; `body` starts at its first `##` section."""

    id: str
    tipo: str
    titulo: str
    vigente_desde: date
    ejemplo: bool
    body: str


def parse_kb_document(text: str, *, source_name: str) -> KbDocument:
    """Parse and validate a `kb/*.md` document's text.

    `source_name` (typically the file name) identifies the document in error messages.
    """

    def invalid(problem: str) -> InvalidKbDocument:
        return InvalidKbDocument(f"El documento «{source_name}» no es válido: {problem}")

    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        raise invalid(
            "no tiene cabecera. El archivo debe empezar con una cabecera (frontmatter) "
            "delimitada por dos líneas «---», con los campos id, tipo, titulo y vigente_desde."
        )
    _, raw_frontmatter, body = parts

    try:
        meta = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        raise invalid(
            "la cabecera entre las líneas «---» no se puede leer. Revisa que cada línea tenga "
            "la forma «campo: valor»."
        ) from exc
    if not isinstance(meta, dict):
        raise invalid(
            "la cabecera entre las líneas «---» debe ser una lista de campos con la forma "
            "«campo: valor»."
        )

    for field in REQUIRED_FIELDS:
        if meta.get(field) in (None, ""):
            raise invalid(
                f"falta el campo obligatorio «{field}» en la cabecera. Añade una línea "
                f"«{field}: …» entre las líneas «---»."
            )

    vigente_desde = meta["vigente_desde"]
    if not isinstance(vigente_desde, date):
        raise invalid(
            f"el campo «vigente_desde» debe ser una fecha con el formato AAAA-MM-DD "
            f"(por ejemplo: 2026-01-31), pero contiene «{vigente_desde}»."
        )

    ejemplo = meta.get("ejemplo", False)
    if not isinstance(ejemplo, bool):
        raise invalid(
            f"el campo «ejemplo» solo puede valer true o false, pero contiene «{ejemplo}»."
        )

    first_section = SECTION_HEADING.search(body)
    if first_section is None or body[: first_section.start()].strip():
        raise invalid(
            "tiene texto fuera de una sección. Todo el contenido debe ir dentro de una sección "
            "que empiece con un encabezado de nivel 2, es decir, una línea que comience por "
            "«## » (por ejemplo: «## Precio»). Mueve ese texto debajo de un encabezado «## » o "
            "crea uno nuevo para él."
        )

    return KbDocument(
        id=str(meta["id"]),
        tipo=str(meta["tipo"]),
        titulo=str(meta["titulo"]),
        vigente_desde=vigente_desde,
        ejemplo=ejemplo,
        body=body[first_section.start() :],
    )
