"""T2 — `Fragment` entity and chunking: one fragment per `##` section (R1, R2)."""

from datetime import date

from app.domain.retrieval.chunking import chunk_document
from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.kb_document import KbDocument


def _doc(body: str) -> KbDocument:
    return KbDocument(
        id="TAR-001",
        tipo="tarifa",
        titulo="Tarifas generales",
        vigente_desde=date(2026, 1, 1),
        ejemplo=True,
        body=body,
    )


THREE_SECTIONS = """## Limpieza dental

Cuesta 60 €.

## Blanqueamiento

Cuesta 280 €.

## Primera visita

Es gratuita.
"""


def test_three_sections_produce_three_fragments_each_carrying_the_titulo():
    fragments = chunk_document(_doc(THREE_SECTIONS))

    assert len(fragments) == 3
    assert all(f.titulo == "Tarifas generales" for f in fragments)
    assert all(f.text.startswith("Tarifas generales") for f in fragments)


def test_each_fragment_holds_its_own_section_and_the_document_metadata():
    first, second, third = chunk_document(_doc(THREE_SECTIONS))

    assert first == Fragment(
        text="Tarifas generales\n\n## Limpieza dental\n\nCuesta 60 €.",
        titulo="Tarifas generales",
        source_id="TAR-001",
        tipo="tarifa",
        vigente_desde=date(2026, 1, 1),
        ejemplo=True,
    )
    assert "Blanqueamiento" in second.text and "280 €" in second.text
    assert "Primera visita" in third.text and "60 €" not in third.text
    assert first.score is None


def test_deeper_headings_do_not_start_a_new_fragment():
    body = "## Horario\n\nDe 9:00 a 14:00.\n\n### Agosto\n\nSolo mañanas.\n"

    fragments = chunk_document(_doc(body))

    assert len(fragments) == 1
    assert "### Agosto" in fragments[0].text
