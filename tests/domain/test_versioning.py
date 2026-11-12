"""T3 — "current version per id" selection with an injectable `today` (R5)."""

from datetime import UTC, date, datetime

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.versioning import madrid_today, select_current_versions

TODAY = date(2026, 6, 15)


def _fragment(source_id: str, vigente_desde: date, text: str = "texto") -> Fragment:
    return Fragment(
        text=text,
        titulo="Tarifas",
        source_id=source_id,
        tipo="tarifa",
        vigente_desde=vigente_desde,
        ejemplo=True,
    )


def test_only_the_current_version_is_selected_between_a_past_and_a_future_one():
    current = _fragment("TAR-001", date(2026, 1, 1))
    future = _fragment("TAR-001", date(2026, 9, 1))

    assert select_current_versions([future, current], today=TODAY) == [current]


def test_the_most_recent_past_version_supersedes_older_ones():
    superseded = _fragment("TAR-001", date(2025, 1, 1))
    current = _fragment("TAR-001", date(2026, 1, 1))

    assert select_current_versions([superseded, current], today=TODAY) == [current]


def test_a_version_starting_today_is_already_current():
    starts_today = _fragment("TAR-001", TODAY)

    assert select_current_versions([starts_today], today=TODAY) == [starts_today]


def test_all_fragments_of_the_current_version_are_kept_and_ids_are_independent():
    tar_a = _fragment("TAR-001", date(2026, 1, 1), "sección A")
    tar_b = _fragment("TAR-001", date(2026, 1, 1), "sección B")
    tar_old = _fragment("TAR-001", date(2025, 1, 1))
    hor = _fragment("HOR-001", date(2024, 1, 1))
    hor_future_only = _fragment("HOR-002", date(2027, 1, 1))

    selected = select_current_versions([tar_a, tar_old, hor, tar_b, hor_future_only], today=TODAY)

    assert selected == [tar_a, hor, tar_b]


def test_madrid_today_uses_the_clinic_timezone_across_the_utc_day_boundary():
    # 23:30 UTC on 1 March is already 00:30 on 2 March in Madrid (CET, UTC+1).
    assert madrid_today(datetime(2026, 3, 1, 23, 30, tzinfo=UTC)) == date(2026, 3, 2)
