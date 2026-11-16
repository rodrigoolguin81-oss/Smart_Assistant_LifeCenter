"""SPEC-001 T5: validate a model answer against the retrieved fragments (R10, R11; NFR-06)."""

from datetime import date

import pytest

from app.domain.answering.validation import ValidationFailure, validate_answer
from app.domain.retrieval.fragment import Fragment


def fragment(source_id: str, text: str, tipo: str = "tarifa", day: date = date(2026, 1, 1)):
    return Fragment(
        text=text, titulo="Título", source_id=source_id, tipo=tipo, vigente_desde=day,
        ejemplo=True, score=0.5,
    )


LIMPIEZA = fragment("TAR-001", "La limpieza dental con revisión cuesta 60 €. Dura unos 45 minutos.")
BLANQUEAMIENTO = fragment("TAR-002", "El blanqueamiento dental en clínica cuesta 280 €.")
HORARIO = fragment("HOR-001", "La clínica abre de lunes a viernes de 9:00 a 14:00.", tipo="horario")
SEGURO = fragment("SEG-001", "Los asegurados de Mutua X tienen un 20 % de descuento.", tipo="seguro")
RETRIEVED = [LIMPIEZA, BLANQUEAMIENTO, HORARIO, SEGURO]

TAR1, TAR2, HOR, SEG = (f.cita for f in RETRIEVED)


@pytest.mark.parametrize(
    "answer",
    [
        f"La limpieza cuesta 60 € {TAR1}.",
        f"La limpieza cuesta 60€ {TAR1}.",  # format-only difference
        f"La limpieza cuesta 60,00 euros {TAR1}.",
        f"Abrimos a las 09:00 {HOR}.",  # 09:00 vs 9:00 in the fragment
        f"Abrimos a las 9 h y cerramos a las 14:00 {HOR}.",
        f"Tienes un 20% de descuento {SEG}.",
        f"Limpieza: 60 € {TAR1}; blanqueamiento: 280 € {TAR2}.",
        f"La limpieza dura unos 45 minutos {TAR1}.",  # durations are not validated figures
    ],
)
def test_grounded_answers_are_accepted(answer):
    result = validate_answer(answer, RETRIEVED)

    assert result.ok, result.failure
    assert result.failure is None


def test_accepted_result_lists_the_cited_fragments_and_citations_once():
    answer = f"Cuesta 60 € {TAR1}. Repito: 60 € {TAR1}. Abrimos a las 9:00 {HOR}."

    result = validate_answer(answer, RETRIEVED)

    assert result.citations == (TAR1, HOR)
    assert result.cited_fragments == (LIMPIEZA, HORARIO)


def test_every_retrieved_section_of_a_cited_document_counts_as_cited():
    """A citation is per document version: all its retrieved sections back the answer."""
    other_section = fragment("TAR-001", "La radiografía panorámica cuesta 30 €.")

    result = validate_answer(f"La radiografía cuesta 30 € {TAR1}.", [LIMPIEZA, other_section])

    assert result.ok
    assert result.cited_fragments == (LIMPIEZA, other_section)


@pytest.mark.parametrize(
    "answer, failure",
    [
        ("La limpieza cuesta 60 €.", ValidationFailure.NO_CITATION),
        ("No tengo información sobre eso.", ValidationFailure.NO_CITATION),
        ("La limpieza cuesta 60 € [TAR-999 | vigente desde 01/01/2026].",
         ValidationFailure.UNKNOWN_CITATION),
        ("La limpieza cuesta 60 € [TAR-001 | vigente desde 01/01/2025].",  # wrong date
         ValidationFailure.UNKNOWN_CITATION),
        (f"Cuesta 60 € {TAR1} y la ortodoncia 3000 € [ORT-001 | vigente desde 01/01/2026].",
         ValidationFailure.UNKNOWN_CITATION),
        (f"Cuesta 60 € {TAR1} [TAR-001].", ValidationFailure.MALFORMED_CITATION),
        (f"Cuesta 60 € [fuente: tarifas] {TAR1}.", ValidationFailure.MALFORMED_CITATION),
        (f"La limpieza cuesta 65 € {TAR1}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),
        # 280 € is in a retrieved fragment, but not in the one the answer cites.
        (f"La limpieza cuesta 280 € {TAR1}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),
        (f"La limpieza cuesta sesenta euros {TAR1}.", ValidationFailure.UNVALIDATABLE_CURRENCY),
        (f"El precio se indica en EUR {TAR1}.", ValidationFailure.UNVALIDATABLE_CURRENCY),
        (f"Son unos euros {TAR1}.", ValidationFailure.UNVALIDATABLE_CURRENCY),
        (f"La limpieza cuesta 65 EUR {TAR1}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),
        (f"Abrimos a las 9:30 {HOR}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),
        (f"Abrimos a las 8 h {HOR}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),
        (f"Abrimos a las 9:00 {TAR1}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),  # wrong source
        (f"Tienes un 25 % de descuento {SEG}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),
        (f"La limpieza cuesta 60 % {TAR1}.", ValidationFailure.FIGURE_NOT_IN_SOURCE),  # kind
    ],
)
def test_ungrounded_answers_are_rejected_with_the_failure_kind(answer, failure):
    result = validate_answer(answer, RETRIEVED)

    assert not result.ok
    assert result.failure is failure
    assert result.citations == ()
    assert result.cited_fragments == ()


def test_nothing_retrieved_means_no_citation_can_be_valid():
    assert validate_answer(f"Cuesta 60 € {TAR1}.", []).failure is ValidationFailure.UNKNOWN_CITATION
