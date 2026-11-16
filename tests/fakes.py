"""Test doubles for SPEC-001. Tests never call Gemini: they use `FakeLanguageModel` instead.

`FakeLanguageModel` is duck-typed against the `LanguageModel` port (defined in T7): it returns
(or raises) scripted items in order and records every prompt it receives, so tests can assert
whether — and how many times — the model was called.
"""

from collections.abc import Iterable
from datetime import date
from typing import Any

from app.domain.retrieval.fragment import Fragment


class FakeLanguageModel:
    def __init__(self, script: Iterable[Any]):
        self._script = list(script)
        self.calls: list[Any] = []

    def generate(self, prompt: Any, timeout_seconds: float) -> Any:
        self.calls.append(prompt)
        assert self._script, "FakeLanguageModel: no scripted reply left for this call"
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeKnowledgeRepository:
    """In-memory `KnowledgeRepository`: returns the given fragments by descending score."""

    def __init__(self, fragments: Iterable[Fragment]):
        self._fragments = sorted(fragments, key=lambda f: f.score or 0.0, reverse=True)
        self.queries: list[str] = []

    def search(self, query: str, k: int = 5, today: date | None = None) -> list[Fragment]:
        self.queries.append(query)
        return self._fragments[:k]
