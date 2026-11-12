"""Relevance threshold (R8) and the retrieval use case. Pure — the repository is injected."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.ports import KnowledgeRepository

DEFAULT_RELEVANCE_THRESHOLD = 0.02
"""Placeholder cutoff over the normalized ts_rank score (option 32, 0–1).

Open assumption (clarifications.md): to be tuned against eval NFR-03. Chosen below the lowest
top score observed for queries that do match the example kb/ (≈0.037).
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
