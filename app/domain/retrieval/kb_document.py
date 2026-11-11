"""Knowledge base document schema (R1): Markdown with YAML frontmatter. Pure — no I/O."""

from dataclasses import dataclass
from datetime import date

import yaml

REQUIRED_FIELDS = ("id", "tipo", "titulo", "vigente_desde")


class InvalidKbDocument(ValueError):
    """A `kb/*.md` document does not satisfy the frontmatter schema."""


@dataclass(frozen=True)
class KbDocument:
    id: str
    tipo: str
    titulo: str
    vigente_desde: date
    ejemplo: bool
    body: str


def parse_kb_document(text: str) -> KbDocument:
    """Parse and validate a `kb/*.md` document's text."""
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        raise InvalidKbDocument("document has no YAML frontmatter delimited by '---'")
    _, raw_frontmatter, body = parts

    try:
        meta = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        raise InvalidKbDocument(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise InvalidKbDocument("frontmatter must be a YAML mapping")

    for field in REQUIRED_FIELDS:
        if meta.get(field) in (None, ""):
            raise InvalidKbDocument(f"missing required frontmatter field: {field}")

    vigente_desde = meta["vigente_desde"]
    if not isinstance(vigente_desde, date):
        raise InvalidKbDocument(f"vigente_desde must be a YYYY-MM-DD date, got {vigente_desde!r}")

    ejemplo = meta.get("ejemplo", False)
    if not isinstance(ejemplo, bool):
        raise InvalidKbDocument(f"ejemplo must be true or false, got {ejemplo!r}")

    return KbDocument(
        id=str(meta["id"]),
        tipo=str(meta["tipo"]),
        titulo=str(meta["titulo"]),
        vigente_desde=vigente_desde,
        ejemplo=ejemplo,
        body=body.lstrip("\n"),
    )
