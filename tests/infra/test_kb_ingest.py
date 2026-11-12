"""T5 — idempotent, full-replace ingestion command (R2, R3, R9).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main`.
"""

from pathlib import Path

import pytest

from app.domain.retrieval.kb_document import InvalidKbDocument
from app.infra.kb_ingest import ingest, main

TARIFAS = """---
id: TAR-001
tipo: tarifa
titulo: Tarifas generales
vigente_desde: 2026-01-01
ejemplo: true
---

## Limpieza dental

Cuesta 60 €.

## Blanqueamiento

Cuesta 280 €.
"""

HORARIO = """---
id: HOR-001
tipo: horario
titulo: Horario de apertura
vigente_desde: 2026-01-01
ejemplo: true
---

## Lunes a viernes

De 9:00 a 20:00.
"""

ROWS = """
    SELECT fragment_id, source_id, tipo, titulo, vigente_desde, ejemplo, chunk_text
    FROM kb_fragments ORDER BY fragment_id
"""


@pytest.fixture
def kb_dir(tmp_path: Path) -> Path:
    (tmp_path / "tarifas.md").write_text(TARIFAS, encoding="utf-8")
    (tmp_path / "horario.md").write_text(HORARIO, encoding="utf-8")
    return tmp_path


def _source_ids(conn) -> list[str]:
    return [r[0] for r in conn.execute("SELECT source_id FROM kb_fragments ORDER BY 1").fetchall()]


def test_ingestion_creates_the_schema_and_loads_one_row_per_section(test_db, kb_dir):
    test_db.execute("DROP TABLE IF EXISTS kb_fragments")
    test_db.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS spanish_unaccent")

    report = ingest(test_db, kb_dir)

    assert (report.documents, report.fragments) == (2, 3)
    assert _source_ids(test_db) == ["HOR-001", "TAR-001", "TAR-001"]
    (titulo, ejemplo, chunk_text) = test_db.execute(
        "SELECT titulo, ejemplo, chunk_text FROM kb_fragments WHERE chunk_text LIKE '%%Limpieza%%'"
    ).fetchone()
    assert (titulo, ejemplo) == ("Tarifas generales", True)
    assert chunk_text.startswith("Tarifas generales\n\n## Limpieza dental")


def test_running_twice_on_unchanged_files_neither_duplicates_nor_changes_rows(test_db, kb_dir):
    ingest(test_db, kb_dir)
    first = test_db.execute(ROWS).fetchall()

    ingest(test_db, kb_dir)
    second = test_db.execute(ROWS).fetchall()

    assert len(first) == 3
    assert second == first


def test_removing_a_document_and_re_running_deletes_its_fragments(test_db, kb_dir):
    ingest(test_db, kb_dir)

    (kb_dir / "tarifas.md").unlink()
    ingest(test_db, kb_dir)

    assert _source_ids(test_db) == ["HOR-001"]


def test_an_invalid_document_aborts_ingestion_without_touching_the_table(test_db, kb_dir):
    ingest(test_db, kb_dir)
    before = test_db.execute(ROWS).fetchall()

    (kb_dir / "roto.md").write_text("Sin cabecera ni secciones.\n", encoding="utf-8")
    with pytest.raises(InvalidKbDocument, match="roto.md"):
        ingest(test_db, kb_dir)

    assert test_db.execute(ROWS).fetchall() == before


def test_r11_same_id_and_vigente_desde_is_rejected_naming_both_files(test_db, kb_dir):
    ingest(test_db, kb_dir)
    before = test_db.execute(ROWS).fetchall()

    (kb_dir / "tarifas-copia.md").write_text(TARIFAS, encoding="utf-8")
    with pytest.raises(InvalidKbDocument) as excinfo:
        ingest(test_db, kb_dir)

    message = str(excinfo.value)
    assert "tarifas.md" in message and "tarifas-copia.md" in message
    assert "TAR-001" in message
    assert "vigente_desde distinta" in message
    assert test_db.execute(ROWS).fetchall() == before


def test_r11_same_id_with_different_vigente_desde_ingests_both_versions(test_db, kb_dir):
    nueva_version = TARIFAS.replace("vigente_desde: 2026-01-01", "vigente_desde: 2027-01-01")
    (kb_dir / "tarifas-2027.md").write_text(nueva_version, encoding="utf-8")

    report = ingest(test_db, kb_dir)

    assert (report.documents, report.fragments) == (3, 5)
    versions = test_db.execute(
        "SELECT DISTINCT vigente_desde::text FROM kb_fragments WHERE source_id = 'TAR-001' "
        "ORDER BY 1"
    ).fetchall()
    assert versions == [("2026-01-01",), ("2027-01-01",)]


def test_cli_ingests_against_the_database_named_by_database_url_env(test_db, kb_dir, capsys):
    exit_code = main(["--kb-dir", str(kb_dir), "--database-url-env", "TEST_DATABASE_URL"])

    assert exit_code == 0
    assert _source_ids(test_db) == ["HOR-001", "TAR-001", "TAR-001"]
    assert "2 documentos" in capsys.readouterr().out


def test_cli_reports_an_invalid_document_in_spanish_and_fails(test_db, kb_dir, capsys):
    (kb_dir / "roto.md").write_text("Sin cabecera.\n", encoding="utf-8")

    exit_code = main(["--kb-dir", str(kb_dir), "--database-url-env", "TEST_DATABASE_URL"])

    assert exit_code == 1
    assert "roto.md" in capsys.readouterr().err
