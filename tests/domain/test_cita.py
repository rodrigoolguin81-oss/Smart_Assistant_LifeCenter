"""T9 — source citation `[ID | vigente desde dd/mm/aaaa]` (R6). Pure."""

from datetime import date

import pytest

from app.domain.retrieval.fragment import Fragment


@pytest.mark.parametrize(
    "source_id, vigente_desde, expected",
    [
        ("TAR-001", date(2026, 1, 5), "[TAR-001 | vigente desde 05/01/2026]"),
        ("HOR-001", date(2026, 11, 30), "[HOR-001 | vigente desde 30/11/2026]"),
    ],
)
def test_cita_formats_source_id_and_vigente_desde_as_dd_mm_aaaa(source_id, vigente_desde, expected):
    fragment = Fragment(
        text="…",
        titulo="…",
        source_id=source_id,
        tipo="tarifa",
        vigente_desde=vigente_desde,
        ejemplo=False,
    )

    assert fragment.cita == expected
