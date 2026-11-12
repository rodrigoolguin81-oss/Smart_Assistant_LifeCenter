"""HTTP contract of `POST /internal/retrieval/query` (see plan.md: Contracts)."""

from datetime import date
from typing import Self

from pydantic import BaseModel, Field

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.relevance import RetrievalResult


class RetrievalRequest(BaseModel):
    query: str
    k: int = Field(default=5, ge=1)  # R4: default 5, caller-configurable


class FragmentOut(BaseModel):
    text: str
    titulo: str
    source_id: str
    vigente_desde: date
    cita: str
    ejemplo: bool  # R7: required, never defaulted, so it cannot be silently dropped
    score: float

    @classmethod
    def from_fragment(cls, fragment: Fragment) -> Self:
        return cls(
            text=fragment.text,
            titulo=fragment.titulo,
            source_id=fragment.source_id,
            vigente_desde=fragment.vigente_desde,
            cita=fragment.cita,
            ejemplo=fragment.ejemplo,
            score=fragment.score if fragment.score is not None else 0.0,
        )


class RetrievalResponse(BaseModel):
    fragments: list[FragmentOut]
    below_threshold: bool

    @classmethod
    def from_result(cls, result: RetrievalResult) -> Self:
        return cls(
            fragments=[FragmentOut.from_fragment(f) for f in result.fragments],
            below_threshold=result.below_threshold,
        )
