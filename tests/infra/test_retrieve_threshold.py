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


def test_a_query_matching_the_kb_is_not_below_threshold(test_db):
    ingest(test_db, KB_DIR)
    repo = PostgresKnowledgeRepository(test_db)

    result = retrieve(repo, "cuánto cuesta una limpieza")

    assert result.below_threshold is False
    assert result.fragments[0].source_id == "TAR-001"
