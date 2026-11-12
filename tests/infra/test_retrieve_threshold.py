"""T8 — end to end over the Neon test branch: no lexical overlap → `below_threshold` (R8)."""

from pathlib import Path

from app.domain.retrieval.relevance import retrieve
from app.infra.kb_ingest import ingest
from app.infra.kb_repository import PostgresKnowledgeRepository

KB_DIR = Path(__file__).resolve().parents[2] / "kb"


def test_a_query_with_no_lexical_overlap_is_below_threshold_with_no_fragments(test_db):
    ingest(test_db, KB_DIR)
    repo = PostgresKnowledgeRepository(test_db)

    result = retrieve(repo, "aceptáis el seguro Sanitas para implantes")

    assert result.below_threshold is True
    assert result.fragments == ()


def test_a_long_answerable_question_is_not_cut_by_the_default_threshold(test_db):
    # Lowest-scoring answerable question of the interim eval (≈0.0116): ts_rank dilution over
    # many OR terms. The default threshold (clarifications Q10) must let it through.
    ingest(test_db, KB_DIR)
    repo = PostgresKnowledgeRepository(test_db)

    result = retrieve(
        repo,
        "Buenas, trabajo de lunes a viernes hasta las siete y quería saber hasta qué hora "
        "abrís por la tarde para poder ir después del trabajo",
    )

    assert result.below_threshold is False
    assert "HOR-001" in {f.source_id for f in result.fragments}


def test_a_query_matching_the_kb_is_not_below_threshold(test_db):
    ingest(test_db, KB_DIR)
    repo = PostgresKnowledgeRepository(test_db)

    result = retrieve(repo, "cuánto cuesta una limpieza")

    assert result.below_threshold is False
    assert result.fragments[0].source_id == "TAR-001"
