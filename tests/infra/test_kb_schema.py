"""T4 — `spanish_unaccent` text search configuration and `kb_fragments` migration (R3).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main`.
"""

from datetime import date

import pytest

from app.infra.schema import apply_schema

INSERT = """
    INSERT INTO kb_fragments (source_id, tipo, titulo, vigente_desde, chunk_text)
    VALUES ('T4-TEST', 'tratamiento', 'Ortodoncia', %s, %s)
"""

MATCHES = """
    SELECT count(*) FROM kb_fragments
    WHERE source_id = 'T4-TEST' AND search_vector @@ plainto_tsquery('spanish_unaccent', %s)
"""


def test_schema_is_created_from_scratch_with_a_generated_gin_indexed_search_vector(test_db):
    test_db.execute("DROP TABLE IF EXISTS kb_fragments")
    test_db.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS spanish_unaccent")

    apply_schema(test_db)
    apply_schema(test_db)  # idempotent: re-running must not fail

    is_generated, expression = test_db.execute(
        """
        SELECT is_generated, generation_expression FROM information_schema.columns
        WHERE table_name = 'kb_fragments' AND column_name = 'search_vector'
        """
    ).fetchone()
    assert is_generated == "ALWAYS"
    assert "spanish_unaccent" in expression

    (gin_indexes,) = test_db.execute(
        """
        SELECT count(*) FROM pg_indexes
        WHERE tablename = 'kb_fragments' AND indexdef ILIKE '%USING gin (search_vector)%'
        """
    ).fetchone()
    assert gin_indexes == 1


@pytest.mark.parametrize(
    "stored, query",
    [
        ("Revisión anual de ortodoncia y retirada de brackets.", "revision"),
        ("Revision anual de ortodoncia y retirada de brackets.", "revisión"),
        ("Duración del tratamiento: dieciocho meses.", "duracion"),
    ],
    ids=["accented-text-unaccented-query", "unaccented-text-accented-query", "duracion"],
)
def test_search_vector_is_populated_and_matches_regardless_of_accents(test_db, stored, query):
    apply_schema(test_db)

    with test_db.transaction(force_rollback=True):
        test_db.execute(INSERT, (date(2026, 1, 1), stored))

        (search_vector,) = test_db.execute(
            "SELECT search_vector FROM kb_fragments WHERE source_id = 'T4-TEST'"
        ).fetchone()
        (matches,) = test_db.execute(MATCHES, (query,)).fetchone()

    assert search_vector, "search_vector must be auto-populated by the generated column"
    assert matches == 1
