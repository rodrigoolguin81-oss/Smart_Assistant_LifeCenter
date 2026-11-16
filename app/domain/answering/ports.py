"""Port for the language model the answering domain depends on; infrastructure implements it.

The provider (Gemini in development, clarifications Q1) stays behind this port, so it can be
swapped — e.g. for a paid plan or an EU provider before production — without touching the domain.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.domain.answering.prompt import Prompt

ERROR_KINDS = frozenset({"rate_limited", "timeout", "api_error", "invalid_output"})
"""`rate_limited` = HTTP 429; `invalid_output` = non-JSON or schema mismatch (R16)."""


class LanguageModelError(Exception):
    """Any failure of a model call. The endpoint never retries it (Q12); only evals retry
    `rate_limited` (plan: "Gemini free-tier limits")."""

    def __init__(self, kind: str, message: str, retry_after_seconds: float | None = None):
        if kind not in ERROR_KINDS:
            raise ValueError(f"unknown LanguageModelError kind {kind!r}")
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class ModelReply:
    answerable: bool
    answer: str
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("token counts cannot be negative")


@runtime_checkable
class LanguageModel(Protocol):
    def generate(self, prompt: Prompt, timeout_seconds: float) -> ModelReply:
        """One call, no retries. Raises `LanguageModelError` on any failure."""
        ...
