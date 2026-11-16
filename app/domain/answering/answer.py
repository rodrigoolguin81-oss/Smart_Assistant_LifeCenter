"""`Answer`: the channel-independent result returned to the API (R17). Pure — no I/O.

Every non-answer (abstention or model error) is built by a factory that sets the handoff offer
and never booking (R14, R15). `__post_init__` enforces the same invariants, so no code path can
produce an abstention that offers booking or carries citations.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from app.domain.answering import messages


class Reason(str, Enum):
    ANSWERED = "answered"
    BELOW_THRESHOLD = "below_threshold"
    MODEL_ABSTAINED = "model_abstained"
    VALIDATION_FAILED = "validation_failed"
    LLM_ERROR = "llm_error"


_ABSTENTION_REASONS = frozenset(
    {Reason.BELOW_THRESHOLD, Reason.MODEL_ABSTAINED, Reason.VALIDATION_FAILED}
)


@dataclass(frozen=True)
class Answer:
    answer: str
    abstained: bool
    reason: Reason
    offer_handoff: bool
    handoff_label: str | None
    offer_booking: bool
    citations: tuple[str, ...]
    ejemplo: bool
    error_kind: str | None = None
    """Only on `llm_error` (e.g. `rate_limited`); exposed as the X-LLM-Error-Kind header."""

    def __post_init__(self) -> None:
        if self.abstained != (self.reason is not Reason.ANSWERED):
            raise ValueError("`abstained` must be true for every reason except `answered`")
        if self.abstained:
            if self.offer_booking:
                raise ValueError("an abstained answer can never offer booking (R14)")
            if self.citations:
                raise ValueError("an abstained answer can never carry citations (R15)")
            if not self.offer_handoff:
                raise ValueError("an abstained answer must offer the handoff (R15)")
        elif not self.citations:
            raise ValueError("an answered response needs at least one citation (R10)")
        if (self.error_kind is not None) != (self.reason is Reason.LLM_ERROR):
            raise ValueError("`error_kind` is set only, and always, on `llm_error`")

    @classmethod
    def abstention(cls, reason: Reason) -> "Answer":
        if reason not in _ABSTENTION_REASONS:
            raise ValueError(f"{reason.value!r} is not an abstention reason")
        return cls._non_answer(messages.ABSTENTION_MESSAGE, reason)

    @classmethod
    def llm_error(cls, error_kind: str) -> "Answer":
        return cls._non_answer(messages.LLM_ERROR_MESSAGE, Reason.LLM_ERROR, error_kind)

    @classmethod
    def answered(
        cls, text: str, *, citations: Iterable[str], offer_booking: bool, ejemplo: bool
    ) -> "Answer":
        return cls(
            answer=text,
            abstained=False,
            reason=Reason.ANSWERED,
            offer_handoff=False,
            handoff_label=None,
            offer_booking=offer_booking,
            citations=tuple(citations),
            ejemplo=ejemplo,
        )

    @classmethod
    def _non_answer(cls, text: str, reason: Reason, error_kind: str | None = None) -> "Answer":
        return cls(
            answer=text,
            abstained=True,
            reason=reason,
            offer_handoff=True,
            handoff_label=messages.HANDOFF_LABEL,
            offer_booking=False,
            citations=(),
            ejemplo=False,
            error_kind=error_kind,
        )
