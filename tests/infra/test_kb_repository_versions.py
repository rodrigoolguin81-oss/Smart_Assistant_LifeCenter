"""T7 — current-version filtering (R5) inside the SQL query, before `LIMIT k`.

Runs against the Neon test branch (TEST_DATABASE_URL), never `main`.
"""

from datetime import date
from pathlib import Path

import pytest

from app.infra.kb_ingest import ingest
from app.infra.kb_repository import PostgresKnowledgeRepository

TODAY = date(2026, 6, 15)


def _doc(vigente_desde: str, sections: list[str], doc_id: str = "TAR-001") -> str:
    body = "\n\n".join(f"## Sección {i}\n\n{text}" for i, text in enumerate(sections, 1))
    return (
        f"---\nid: {doc_id}\ntipo: tarifa\ntitulo: Tarifas\nvigente_desde: {vigente_desde}\n"
        f"ejemplo: true\n---\n\n{body}\n"
    )


@pytest.fixture
def make_repo(test_db, tmp_path: Path):
    def _make(files: dict[str, str]) -> PostgresKnowledgeRepository:
        for name, text in files.items():
            (tmp_path / name).write_text(text, encoding="utf-8")
        ingest(test_db, tmp_path)
        return PostgresKnowledgeRepository(test_db)

    return _make


def test_a_superseded_version_is_never_returned_only_the_current_one(make_repo):
    repo = make_repo(
        {
            "tarifas-2025.md": _doc("2025-01-01", ["La limpieza cuesta 50 euros."]),
            "tarifas-2026.md": _doc("2026-01-01", ["La limpieza cuesta 60 euros."]),
            "tarifas-2027.md": _doc("2027-01-01", ["La limpieza cuesta 70 euros."]),
        }
    )

    results = repo.search("limpieza", today=TODAY)

    assert [(f.vigente_desde, "60 euros" in f.text) for f in results] == [(date(2026, 1, 1), True)]


def test_the_injected_today_decides_which_version_is_current(make_repo):
    repo = make_repo(
        {
            "tarifas-2026.md": _doc("2026-01-01", ["La limpieza cuesta 60 euros."]),
            "tarifas-2027.md": _doc("2027-01-01", ["La limpieza cuesta 70 euros."]),
        }
    )

    assert [f.vigente_desde for f in repo.search("limpieza", today=date(2026, 12, 31))] == [
        date(2026, 1, 1)
    ]
    assert [f.vigente_desde for f in repo.search("limpieza", today=date(2027, 1, 1))] == [
        date(2027, 1, 1)
    ]


def test_stale_matches_never_take_top_k_slots_from_current_fragments(make_repo):
    # Superseded and future versions repeat the term, so they would outrank the current ones.
    # Filtering after LIMIT k would leave no current fragment; filtering in SQL returns k.
    loud = "Limpieza, limpieza y más limpieza: limpieza dental completa."
    repo = make_repo(
        {
            "tarifas-2025.md": _doc("2025-01-01", [loud, loud, loud]),
            "tarifas-2026.md": _doc(
                "2026-01-01",
                ["Precio de la limpieza.", "Duración de la limpieza.", "Cita para limpieza."],
            ),
            "tarifas-2027.md": _doc("2027-01-01", [loud, loud, loud]),
        }
    )

    results = repo.search("limpieza", k=3, today=TODAY)

    assert len(results) == 3
    assert {f.vigente_desde for f in results} == {date(2026, 1, 1)}


def test_a_document_whose_only_version_is_future_dated_is_not_returned(make_repo):
    repo = make_repo(
        {
            "tarifas.md": _doc("2026-01-01", ["La limpieza cuesta 60 euros."]),
            "seguros.md": _doc("2027-01-01", ["Limpieza cubierta por el seguro."], "SEG-001"),
        }
    )

    assert {f.source_id for f in repo.search("limpieza seguro", today=TODAY)} == {"TAR-001"}


def test_without_an_injected_today_the_clinic_date_is_used(make_repo):
    repo = make_repo(
        {
            "tarifas.md": _doc("2020-01-01", ["La limpieza cuesta 60 euros."]),
            "tarifas-futuras.md": _doc("2999-01-01", ["La limpieza cuesta 999 euros."]),
        }
    )

    assert [f.vigente_desde for f in repo.search("limpieza")] == [date(2020, 1, 1)]
