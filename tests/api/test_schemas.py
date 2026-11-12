"""T9 — mapping `Fragment` → API response: `titulo`, `cita` and `ejemplo` (R6, R7)."""

from datetime import date

import pytest

from app.api.schemas import RetrievalResponse
from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.relevance import RetrievalResult


def _fragment(ejemplo: bool) -> Fragment:
    return Fragment(
        text="Tarifas generales\n\n## Limpieza dental\n\nCuesta 60 €.",
        titulo="Tarifas generales",
        source_id="TAR-001",
        tipo="tarifa",
        vigente_desde=date(2026, 1, 5),
        ejemplo=ejemplo,
        score=0.0436,
    )


def test_a_fragment_from_an_ejemplo_document_keeps_the_flag_and_a_formatted_cita():
    result = RetrievalResult(fragments=(_fragment(ejemplo=True),), below_threshold=False)

    body = RetrievalResponse.from_result(result).model_dump(mode="json")

    assert body == {
        "fragments": [
            {
                "text": "Tarifas generales\n\n## Limpieza dental\n\nCuesta 60 €.",
                "titulo": "Tarifas generales",
                "source_id": "TAR-001",
                "vigente_desde": "2026-01-05",
                "cita": "[TAR-001 | vigente desde 05/01/2026]",
                "ejemplo": True,
                "score": 0.0436,
            }
        ],
        "below_threshold": False,
    }


@pytest.mark.parametrize("ejemplo", [True, False])
def test_the_ejemplo_flag_is_never_dropped_or_defaulted(ejemplo):
    result = RetrievalResult(fragments=(_fragment(ejemplo),), below_threshold=False)

    body = RetrievalResponse.from_result(result).model_dump(mode="json")

    assert body["fragments"][0]["ejemplo"] is ejemplo


def test_below_threshold_maps_to_an_empty_fragment_list():
    result = RetrievalResult(fragments=(), below_threshold=True)

    body = RetrievalResponse.from_result(result).model_dump(mode="json")

    assert body == {"fragments": [], "below_threshold": True}
