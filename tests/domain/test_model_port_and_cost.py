"""SPEC-001 T7: the `LanguageModel` port, its error type, and the cost estimate (R16, R18)."""

from decimal import Decimal

import pytest

from app.domain.answering.cost import ModelPrices, estimate_cost_eur
from app.domain.answering.ports import (
    ERROR_KINDS,
    LanguageModel,
    LanguageModelError,
    ModelReply,
)
from tests.fakes import FakeLanguageModel


def test_error_kinds_are_the_four_from_the_plan():
    assert ERROR_KINDS == {"rate_limited", "timeout", "api_error", "invalid_output"}


@pytest.mark.parametrize("kind", sorted(ERROR_KINDS))
def test_language_model_error_carries_its_kind(kind):
    error = LanguageModelError(kind, "detalle")

    assert error.kind == kind
    assert error.retry_after_seconds is None
    assert "detalle" in str(error)


def test_rate_limited_error_can_carry_the_server_retry_delay():
    error = LanguageModelError("rate_limited", "429", retry_after_seconds=12.5)

    assert error.retry_after_seconds == 12.5


def test_language_model_error_rejects_an_unknown_kind():
    with pytest.raises(ValueError):
        LanguageModelError("quota", "desconocido")


def test_model_reply_rejects_negative_token_counts():
    with pytest.raises(ValueError):
        ModelReply(answerable=True, answer="x", input_tokens=-1, output_tokens=0)


def test_the_fake_model_satisfies_the_port():
    assert isinstance(FakeLanguageModel([]), LanguageModel)


PRICES = ModelPrices(input_eur_per_mtok=Decimal("0.70"), output_eur_per_mtok=Decimal("3.50"))


def test_cost_is_tokens_times_price_per_million():
    # 1 500 × 0.70 / 1e6 + 150 × 3.50 / 1e6 = 0.00105 + 0.000525
    assert estimate_cost_eur(1500, 150, PRICES) == Decimal("0.001575")


def test_zero_tokens_cost_nothing():
    assert estimate_cost_eur(0, 0, PRICES) == Decimal("0")


def test_cost_is_exact_decimal_arithmetic():
    prices = ModelPrices(Decimal("0.1"), Decimal("0.2"))

    assert estimate_cost_eur(3, 0, prices) == Decimal("0.0000003")


@pytest.mark.parametrize("tokens", [(-1, 0), (0, -5)])
def test_cost_rejects_negative_tokens(tokens):
    with pytest.raises(ValueError):
        estimate_cost_eur(*tokens, PRICES)


def test_prices_reject_negative_values():
    with pytest.raises(ValueError):
        ModelPrices(Decimal("-0.1"), Decimal("1"))


def test_prices_parse_from_configuration_strings():
    """Configuration comes from .env as text; float would lose precision."""
    assert ModelPrices.from_strings("0,70", "3.50") == PRICES


@pytest.mark.parametrize("raw", ["", "  ", "gratis", "NaN", "Infinity", "-0.5"])
def test_prices_reject_missing_or_invalid_configuration(raw):
    with pytest.raises(ValueError, match="LLM_PRICE"):
        ModelPrices.from_strings(raw, "3.50")
