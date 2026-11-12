"""T8 — relevance threshold over the normalized ts_rank score and `below_threshold` (R8). Pure."""

from datetime import date

import pytest

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.relevance import (
    DEFAULT_RELEVANCE_THRESHOLD,
    RetrievalResult,
    apply_relevance_threshold,
    retrieve,
)


def _fragment(score: float) -> Fragment:
    return Fragment(
        text="Tarifas\n\n## Limpieza",
        titulo="Tarifas",
        source_id="TAR-001",
        tipo="tarifa",
        vigente_desde=date(2026, 1, 1),
        ejemplo=True,
        score=score,
    )


class FakeRepository:
    def __init__(self, results: list[Fragment]) -> None:
        self.results = results
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, today: date | None = None) -> list[Fragment]:
        self.calls.append((query, k, today))
        return self.results


def test_no_fragments_at_all_is_below_threshold():
    assert apply_relevance_threshold([], threshold=0.02) == RetrievalResult(
        fragments=(), below_threshold=True
    )


def test_a_top_score_below_the_threshold_returns_no_fragments():
    low = [_fragment(0.015), _fragment(0.01)]

    assert apply_relevance_threshold(low, threshold=0.02) == RetrievalResult(
        fragments=(), below_threshold=True
    )


@pytest.mark.parametrize("top_score", [0.02, 0.05])
def test_a_top_score_at_or_above_the_threshold_returns_the_fragments(top_score):
    results = [_fragment(top_score), _fragment(0.01)]

    assert apply_relevance_threshold(results, threshold=0.02) == RetrievalResult(
        fragments=tuple(results), below_threshold=False
    )


def test_the_default_threshold_is_a_normalized_score_in_the_0_1_range():
    assert 0 < DEFAULT_RELEVANCE_THRESHOLD < 1


def test_retrieve_searches_the_repository_and_applies_the_threshold():
    repo = FakeRepository([_fragment(0.01)])
    today = date(2026, 6, 15)

    result = retrieve(repo, "limpieza", k=3, today=today, threshold=0.02)

    assert repo.calls == [("limpieza", 3, today)]
    assert result == RetrievalResult(fragments=(), below_threshold=True)


def test_retrieve_defaults_to_k_5_and_the_default_threshold():
    repo = FakeRepository([_fragment(DEFAULT_RELEVANCE_THRESHOLD)])

    result = retrieve(repo, "limpieza")

    assert repo.calls == [("limpieza", 5, None)]
    assert result.below_threshold is False
