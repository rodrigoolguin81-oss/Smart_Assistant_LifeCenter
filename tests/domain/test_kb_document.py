"""T1 — `kb/*.md` frontmatter schema (R1) and content-inside-`##` rule (R10)."""

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


def _parse(text: str) -> KbDocument:
    return parse_kb_document(text, source_name="tarifas.md")


def test_parses_a_valid_document():
    doc = _parse(_doc(VALID_FIELDS))

    assert doc == KbDocument(
        id="TAR-001",
        tipo="tarifa",
        titulo="Tarifas generales",
        vigente_desde=date(2026, 1, 1),
        ejemplo=False,
        body="## Limpieza\n\n60 €\n",
    )


def test_ejemplo_flag_is_read_from_frontmatter():
    doc = _parse(_doc({**VALID_FIELDS, "ejemplo": "true"}))

    assert doc.ejemplo is True


def _error_message(text: str) -> str:
    with pytest.raises(InvalidKbDocument) as excinfo:
        _parse(text)
    return str(excinfo.value)


@pytest.mark.parametrize("missing", ["id", "tipo", "titulo", "vigente_desde"])
def test_rejects_a_document_missing_a_required_field(missing):
    fields = {k: v for k, v in VALID_FIELDS.items() if k != missing}

    message = _error_message(_doc(fields))

    assert "tarifas.md" in message
    assert f"«{missing}»" in message
    assert "falta el campo obligatorio" in message


def test_rejects_a_vigente_desde_that_is_not_a_date():
    message = _error_message(_doc({**VALID_FIELDS, "vigente_desde": "enero"}))

    assert "tarifas.md" in message
    assert "«vigente_desde»" in message
    assert "fecha" in message and "AAAA-MM-DD" in message


def test_rejects_an_ejemplo_flag_that_is_not_true_or_false():
    message = _error_message(_doc({**VALID_FIELDS, "ejemplo": "quizás"}))

    assert "tarifas.md" in message
    assert "«ejemplo»" in message
    assert "true" in message and "false" in message


def test_rejects_a_document_without_frontmatter():
    message = _error_message("## Limpieza\n\n60 €\n")

    assert "tarifas.md" in message
    assert "cabecera" in message and "---" in message


@pytest.mark.parametrize(
    "frontmatter",
    ["id: [TAR-001", "- solo\n- una lista"],
    ids=["malformed-yaml", "not-a-mapping"],
)
def test_rejects_a_frontmatter_that_cannot_be_read(frontmatter):
    message = _error_message(f"---\n{frontmatter}\n---\n\n## Limpieza\n\n60 €\n")

    assert "tarifas.md" in message
    assert "cabecera" in message


@pytest.mark.parametrize(
    "body",
    [
        "Introducción sin sección.\n\n## Limpieza\n\n60 €\n",
        "Documento sin ningún encabezado de nivel 2.\n",
        "### Solo un subapartado\n\n60 €\n",
    ],
    ids=["text-before-first-section", "no-sections", "only-deeper-heading"],
)
def test_rejects_content_outside_a_level_2_section_naming_the_file_in_spanish(body):
    with pytest.raises(InvalidKbDocument) as excinfo:
        _parse(_doc(VALID_FIELDS, body=body))

    message = str(excinfo.value)
    assert "tarifas.md" in message
    assert "todo el contenido" in message.lower()
    assert "sección" in message and "##" in message


def test_blank_lines_before_the_first_section_are_allowed():
    doc = _parse(_doc(VALID_FIELDS, body="\n\n   \n## Limpieza\n\n60 €\n"))

    assert doc.body.startswith("## Limpieza")


def test_kb_example_documents_are_valid_and_cover_required_tipos():
    docs = [
        parse_kb_document(p.read_text(encoding="utf-8"), source_name=p.name)
        for p in sorted(KB_DIR.glob("*.md"))
    ]

    assert {d.tipo for d in docs} >= {"tarifa", "horario", "tratamiento"}
    assert all(d.ejemplo for d in docs), "until PRD DEP-01, every kb/ doc must be ejemplo: true"
