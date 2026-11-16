"""SPEC-001 T4: extract and normalize euro amounts, times and percentages (R10 c, d).

Normalization removes trivial format differences only; a change of value never matches
(plan: "Figure normalization").
"""

from decimal import Decimal

import pytest

from app.domain.answering.figures import Figure, extract_figures, unvalidatable_currency


def only(text: str) -> Figure:
    figures = extract_figures(text)
    assert len(figures) == 1, f"expected one figure in {text!r}, got {figures}"
    return figures[0]


@pytest.mark.parametrize(
    "group",
    [
        ["60 €", "60€", "€60", "€ 60", "60,00 €", "60.00 €", "60 euros", "60 EUR", "60 Euros"],
        ["1.200 €", "1200 €", "1,200 €", "1.200,00 €"],
        ["09:00", "9:00", "9 h", "9h"],
        ["20 %", "20%", "20 por ciento"],
        ["20,5 %", "20.5%"],
    ],
)
def test_trivial_format_differences_normalize_to_the_same_figure(group):
    figures = {only(f"Dato: {text}.") for text in group}
    assert len(figures) == 1, figures


def test_canonical_values():
    assert only("cuesta 60,00 €") == Figure("euro", Decimal("60"))
    assert only("cuesta 1.200 €") == Figure("euro", Decimal("1200"))
    assert only("abre a las 09:30") == Figure("time", (9, 30))
    assert only("abre a las 9 h") == Figure("time", (9, 0))
    assert only("un 20,5 %") == Figure("percent", Decimal("20.5"))


@pytest.mark.parametrize(
    "a, b",
    [
        ("60 €", "65 €"),
        ("60 €", "6,0 €"),
        ("9:30", "9:00"),
        ("19:00", "9:00"),
        ("20 %", "25 %"),
        ("60 €", "60 %"),  # different kind
    ],
)
def test_changes_of_value_or_kind_never_match(a, b):
    assert only(a) != only(b)


def test_extracts_every_figure_in_order():
    text = "La limpieza cuesta 60 € y el blanqueamiento 280 €; abrimos de 9:00 a 14:00, 10 % dto."

    assert extract_figures(text) == [
        Figure("euro", Decimal("60")),
        Figure("euro", Decimal("280")),
        Figure("time", (9, 0)),
        Figure("time", (14, 0)),
        Figure("percent", Decimal("10")),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Dura unos 45 minutos y la realiza la higienista.",
        "Pide cita el 15/12/2026.",
        "Somos 2 odontólogos y 3 gabinetes.",
        "Llámanos, estamos en la calle Mayor 12.",
    ],
)
def test_other_numbers_are_not_figures(text):
    assert extract_figures(text) == []


@pytest.mark.parametrize(
    "text, mention",
    [
        ("Cuesta sesenta euros.", "euros"),
        ("Cuesta unos euros.", "euros"),
        ("El precio es en EUR.", "EUR"),
        ("Son doscientos ochenta €.", "€"),
        ("Cuesta un euro.", "euro"),
    ],
)
def test_currency_without_a_digit_amount_is_unvalidatable(text, mention):
    assert unvalidatable_currency(text) == [mention]
    assert not [f for f in extract_figures(text) if f.kind == "euro"]


@pytest.mark.parametrize("text", ["Cuesta 60 €.", "Cuesta 60 EUR.", "Cuesta €60.", "Son 60 euros."])
def test_currency_attached_to_a_digit_amount_is_validatable(text):
    assert unvalidatable_currency(text) == []


def test_a_malformed_number_next_to_currency_is_unvalidatable():
    """'1.2345 €' fits no separator rule, so it cannot be compared: it must not pass."""
    assert extract_figures("Cuesta 1.2345 €") == []
    assert unvalidatable_currency("Cuesta 1.2345 €") == ["€"]
