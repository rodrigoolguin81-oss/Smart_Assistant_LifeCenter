"""Figures in a text — euro amounts, times, percentages — normalized for comparison (R10 c, d).

The answer and the cited fragments go through this same extractor; validation then checks that
every `(kind, value)` of the answer is among the fragments'. Normalization removes trivial format
differences only, never a change of value (plan: "Figure normalization"):

- euro: digits with `€` before/after (spaces optional), or followed by `EUR` / `euro(s)`;
  value is a `Decimal` (60 € = 60,00 € = 60 euros).
- time: `H:MM` / `HH:MM` or `9 h`; value is `(hour, minute)` (09:00 = 9:00 = 9 h).
- percent: digits followed by `%` or `por ciento`; value is a `Decimal`.

Separators: `,` or `.` followed by exactly 3 digits is a thousands separator, by 1–2 digits a
decimal one (1.200 = 1200; 20,5 = 20.5). A number that fits neither rule is not a figure, so a
currency next to it stays unvalidatable. Other numbers (durations, counts, dates) are not figures.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

FigureKind = Literal["euro", "time", "percent"]


@dataclass(frozen=True)
class Figure:
    kind: FigureKind
    value: Decimal | tuple[int, int]


_NUM = r"\d+(?:[.,]\d+)*"
_START = r"(?<![\d.,:/])"
_CURRENCY_WORD = r"(?i:(?<![a-záéíóúüñ])eur(?:os?)?(?![a-záéíóúüñ]))"
_HOUR = r"[01]?\d|2[0-3]"

FIGURE = re.compile(
    rf"€\s*(?P<euro_pre>{_NUM})"
    rf"|{_START}(?P<euro_suf>{_NUM})\s*(?:€|{_CURRENCY_WORD})"
    rf"|{_START}(?P<pct>{_NUM})\s*(?:%|(?i:por\s+ciento)\b)"
    rf"|{_START}(?P<hh>{_HOUR}):(?P<mm>[0-5]\d)(?!\d)"
    rf"|{_START}(?P<h>{_HOUR})\s*h\b"
)
CURRENCY_MENTION = re.compile(rf"€|{_CURRENCY_WORD}")


def extract_figures(text: str) -> list[Figure]:
    """Every comparable figure in `text`, in order of appearance."""
    return [figure for figure, _ in _scan(text) if figure is not None]


def unvalidatable_currency(text: str) -> list[str]:
    """Currency mentions not attached to a digit amount that can be compared (R10 c).

    E.g. "sesenta euros", a bare "EUR", or "1.2345 €" (a number that fits no separator rule).
    """
    covered = [span for figure, span in _scan(text) if figure is not None and figure.kind == "euro"]
    return [
        mention.group()
        for mention in CURRENCY_MENTION.finditer(text)
        if not any(start <= mention.start() < end for start, end in covered)
    ]


def _scan(text: str) -> list[tuple[Figure | None, tuple[int, int]]]:
    """Each figure-shaped match with its span; `None` when its number cannot be normalized."""
    results = []
    for match in FIGURE.finditer(text):
        groups = match.groupdict()
        figure: Figure | None
        if groups["euro_pre"] or groups["euro_suf"]:
            amount = _parse_number(groups["euro_pre"] or groups["euro_suf"])
            figure = Figure("euro", amount) if amount is not None else None
        elif groups["pct"]:
            amount = _parse_number(groups["pct"])
            figure = Figure("percent", amount) if amount is not None else None
        elif groups["hh"]:
            figure = Figure("time", (int(groups["hh"]), int(groups["mm"])))
        else:
            figure = Figure("time", (int(groups["h"]), 0))
        results.append((figure, match.span()))
    return results


def _parse_number(raw: str) -> Decimal | None:
    """Apply the separator rule; None if the number fits neither thousands nor decimal use."""
    head, *groups = re.split(r"[.,]", raw)
    decimals = ""
    if groups and len(groups[-1]) in (1, 2):
        decimals = groups.pop()
    if any(len(group) != 3 for group in groups):
        return None
    if groups and len(head) > 3:
        return None
    integer = head + "".join(groups)
    return Decimal(f"{integer}.{decimals}" if decimals else integer)
