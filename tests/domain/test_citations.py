"""SPEC-001 T3: extract `[ID | vigente desde dd/mm/aaaa]` citations from an answer (R10 a, b)."""

from datetime import date

import pytest

from app.domain.answering.citations import extract_citations, malformed_citations
from app.domain.retrieval.fragment import Fragment

TAR = "[TAR-001 | vigente desde 01/01/2026]"
HOR = "[HOR-001 | vigente desde 15/03/2025]"


def test_extracts_every_citation_in_order_of_appearance():
    text = f"La limpieza cuesta 60 € {TAR}. Abrimos a las 9:00 {HOR}. Repito: {TAR}"

    assert extract_citations(text) == [TAR, HOR, TAR]


def test_recognizes_the_exact_string_produced_by_fragment_cita():
    fragment = Fragment(
        text="…",
        titulo="Tarifas",
        source_id="TAR-001",
        tipo="tarifa",
        vigente_desde=date(2026, 1, 1),
        ejemplo=True,
    )

    assert extract_citations(f"Según {fragment.cita}, sí.") == [fragment.cita]


def test_text_without_citations_returns_nothing():
    assert extract_citations("La limpieza cuesta 60 €.") == []
    assert malformed_citations("La limpieza cuesta 60 €.") == []


@pytest.mark.parametrize(
    "fake",
    [
        "[TAR-001]",
        "[TAR-001 vigente desde 01/01/2026]",  # missing "|"
        "[TAR-001 | vigente desde 2026-01-01]",  # other date format
        "[TAR-001 | vigente desde 1/1/2026]",
        "[TAR-001 | desde 01/01/2026]",
        "[TAR-001 | vigente desde 01/01/2026",  # unclosed
        "(TAR-001 | vigente desde 01/01/2026)",
    ],
)
def test_malformed_variants_are_not_citations(fake):
    assert extract_citations(f"Dato {fake} final") == []


@pytest.mark.parametrize(
    "fake",
    [
        "[TAR-001]",
        "[TAR-001 vigente desde 01/01/2026]",
        "[TAR-001 | vigente desde 2026-01-01]",
        "[TAR-001 | desde 01/01/2026]",
        "[fuente: tarifas 2026]",
    ],
)
def test_bracketed_source_references_that_are_not_valid_citations_are_reported(fake):
    """So validation (T5) can reject an answer that cites a source in a non-verifiable way."""
    assert malformed_citations(f"Dato {fake} y además {TAR}") == [fake]


def test_valid_citations_are_not_reported_as_malformed():
    assert malformed_citations(f"Dato {TAR} y {HOR}") == []


def test_brackets_that_are_not_source_references_are_ignored():
    assert malformed_citations("Pulsa [Hablar con recepción] si lo necesitas") == []
