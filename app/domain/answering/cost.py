"""Estimated cost of a model call in euros (R18; NFR-02 ≤ 0.01 € per conversation).

Prices are per million tokens, maintained by hand in configuration (clarifications, Assumptions)
and handled as `Decimal`, never `float`.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class ModelPrices:
    input_eur_per_mtok: Decimal
    output_eur_per_mtok: Decimal

    def __post_init__(self) -> None:
        if self.input_eur_per_mtok < 0 or self.output_eur_per_mtok < 0:
            raise ValueError("model prices cannot be negative")

    @classmethod
    def from_strings(cls, input_eur_per_mtok: str, output_eur_per_mtok: str) -> "ModelPrices":
        """Parse LLM_PRICE_INPUT_EUR_PER_MTOK / LLM_PRICE_OUTPUT_EUR_PER_MTOK (comma or dot)."""
        return cls(
            _parse_price(input_eur_per_mtok, "LLM_PRICE_INPUT_EUR_PER_MTOK"),
            _parse_price(output_eur_per_mtok, "LLM_PRICE_OUTPUT_EUR_PER_MTOK"),
        )


def estimate_cost_eur(input_tokens: int, output_tokens: int, prices: ModelPrices) -> Decimal:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts cannot be negative")
    return (
        input_tokens * prices.input_eur_per_mtok + output_tokens * prices.output_eur_per_mtok
    ) / MILLION


def _parse_price(raw: str, name: str) -> Decimal:
    error = ValueError(f"{name} must be a price >= 0 in EUR per million tokens, got {raw!r}")
    try:
        price = Decimal(raw.strip().replace(",", "."))
    except InvalidOperation:
        raise error from None
    if not price.is_finite() or price < 0:
        raise error
    return price
