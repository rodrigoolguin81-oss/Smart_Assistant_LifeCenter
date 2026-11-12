"""Relevance threshold (R8) and the retrieval use case. Pure — the repository is injected."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.ports import KnowledgeRepository

DEFAULT_RELEVANCE_THRESHOLD = 0.01
"""Cutoff over the normalized ts_rank score (option 32, 0–1). Decision: clarifications.md Q10.

A recall filter, not the abstention guarantee: no lexical threshold separates unanswerable
questions on its own; final abstention (NFR-03) is SPEC-001's responsibility. To be revisited if
SPEC-001 misses NFR-03, and recalibrated with LifeCenter's real data (PRD DEP-01).
"""


@dataclass(frozen=True)
class RetrievalResult:
    fragments: tuple[Fragment, ...]
    below_threshold: bool


def apply_relevance_threshold(
    fragments: Sequence[Fragment], threshold: float = DEFAULT_RELEVANCE_THRESHOLD
) -> RetrievalResult:
    """Report "no sufficiently relevant fragment" when the top score is below `threshold`.

    `fragments` must be ordered by descending score, as the repository returns them.
    """
    if not fragments or (fragments[0].score or 0.0) < threshold:
        return RetrievalResult(fragments=(), below_threshold=True)
    return RetrievalResult(fragments=tuple(fragments), below_threshold=False)


def retrieve(
    repository: KnowledgeRepository,
    query: str,
    k: int = 5,
    today: date | None = None,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
) -> RetrievalResult:
    return apply_relevance_threshold(repository.search(query, k, today), threshold)
