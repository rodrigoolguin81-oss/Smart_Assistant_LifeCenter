"""Validate a model answer against the fragments actually retrieved (R10; NFR-06, PRD R-01).

An answer passes only if:
  (a) it contains at least one well-formed citation `[ID | vigente desde dd/mm/aaaa]`;
  (b) every citation is identical to the `cita` of a retrieved fragment, and there is no
      malformed source reference (e.g. "[TAR-001]") that could not be checked;
  (c) every currency mention belongs to a digit euro amount (no "sesenta euros", no bare "EUR");
  (d) every figure (euro amount, time, percentage) appears — after normalizing trivial format
      differences — in the text of a fragment the answer cites.

Any failure means abstention (R11); the caller never retries and never shows the model's text.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from app.domain.answering.citations import extract_citations, malformed_citations
from app.domain.answering.figures import extract_figures, unvalidatable_currency
from app.domain.retrieval.fragment import Fragment


class ValidationFailure(str, Enum):
    NO_CITATION = "no_citation"
    UNKNOWN_CITATION = "unknown_citation"
    MALFORMED_CITATION = "malformed_citation"
    UNVALIDATABLE_CURRENCY = "unvalidatable_currency"
    FIGURE_NOT_IN_SOURCE = "figure_not_in_source"


@dataclass(frozen=True)
class ValidationResult:
    failure: ValidationFailure | None = None
    citations: tuple[str, ...] = ()
    """Distinct validated citations, in order of first appearance (empty on failure)."""
    cited_fragments: tuple[Fragment, ...] = ()
    """Every retrieved fragment whose `cita` the answer uses (empty on failure)."""

    @property
    def ok(self) -> bool:
        return self.failure is None


def validate_answer(text: str, retrieved: Sequence[Fragment]) -> ValidationResult:
    if malformed_citations(text):
        return ValidationResult(ValidationFailure.MALFORMED_CITATION)

    citations = tuple(dict.fromkeys(extract_citations(text)))
    if not citations:
        return ValidationResult(ValidationFailure.NO_CITATION)

    retrieved_citations = {fragment.cita for fragment in retrieved}
    if any(citation not in retrieved_citations for citation in citations):
        return ValidationResult(ValidationFailure.UNKNOWN_CITATION)

    if unvalidatable_currency(text):
        return ValidationResult(ValidationFailure.UNVALIDATABLE_CURRENCY)

    cited = tuple(fragment for fragment in retrieved if fragment.cita in citations)
    supported = {figure for fragment in cited for figure in extract_figures(fragment.text)}
    if any(figure not in supported for figure in extract_figures(text)):
        return ValidationResult(ValidationFailure.FIGURE_NOT_IN_SOURCE)

    return ValidationResult(citations=citations, cited_fragments=cited)
