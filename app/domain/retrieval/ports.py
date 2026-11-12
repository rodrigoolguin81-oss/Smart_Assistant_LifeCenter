"""Ports the domain depends on; implemented by the infrastructure layer."""

from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.retrieval.fragment import Fragment


@runtime_checkable
class KnowledgeRepository(Protocol):
    def search(self, query: str, k: int = 5, today: date | None = None) -> list[Fragment]:
        """Top `k` current fragments for `query`, by descending relevance score (0–1).

        Only the current version of each document as of `today` is considered (R5);
        `today` defaults to the clinic's date (Europe/Madrid).
        """
        ...
