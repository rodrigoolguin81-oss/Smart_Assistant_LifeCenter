"""T1 — `kb/*.md` frontmatter schema (R1)."""

from datetime import date
from pathlib import Path

import pytest

from app.domain.retrieval.kb_document import InvalidKbDocument, KbDocument, parse_kb_document

KB_DIR = Path(__file__).resolve().parents[2] / "kb"

VALID_FIELDS = {
    "id": "TAR-001",
    "tipo": "tarifa",
    "titulo": "Tarifas generales",
    "vigente_desde": "2026-01-01",
}


def _doc(fields: dict, body: str = "## Limpieza\n\n60 €\n") -> str:
    frontmatter = "\n".join(f"{key}: {value}" for key, value in fields.items())
    return f"---\n{frontmatter}\n---\n\n{body}"


def test_parses_a_valid_document():
    doc = parse_kb_document(_doc(VALID_FIELDS))

    assert doc == KbDocument(
        id="TAR-001",
        tipo="tarifa",
        titulo="Tarifas generales",
        vigente_desde=date(2026, 1, 1),
        ejemplo=False,
        body="## Limpieza\n\n60 €\n",
    )


def test_ejemplo_flag_is_read_from_frontmatter():
    doc = parse_kb_document(_doc({**VALID_FIELDS, "ejemplo": "true"}))

    assert doc.ejemplo is True


@pytest.mark.parametrize("missing", ["id", "tipo", "titulo", "vigente_desde"])
def test_rejects_a_document_missing_a_required_field(missing):
    fields = {k: v for k, v in VALID_FIELDS.items() if k != missing}

    with pytest.raises(InvalidKbDocument, match=missing):
        parse_kb_document(_doc(fields))


def test_rejects_a_vigente_desde_that_is_not_a_date():
    with pytest.raises(InvalidKbDocument, match="vigente_desde"):
        parse_kb_document(_doc({**VALID_FIELDS, "vigente_desde": "enero"}))


def test_rejects_a_document_without_frontmatter():
    with pytest.raises(InvalidKbDocument, match="frontmatter"):
        parse_kb_document("## Limpieza\n\n60 €\n")


def test_kb_example_documents_are_valid_and_cover_required_tipos():
    docs = [parse_kb_document(p.read_text(encoding="utf-8")) for p in sorted(KB_DIR.glob("*.md"))]

    assert {d.tipo for d in docs} >= {"tarifa", "horario", "tratamiento"}
    assert all(d.ejemplo for d in docs), "until PRD DEP-01, every kb/ document must be ejemplo: true"
