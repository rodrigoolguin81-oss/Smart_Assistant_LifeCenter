"""T6 — `KnowledgeRepository.search(query, k=5)`: OR-combined, ts_rank-ordered FTS (R3, R4).

Runs against the Neon test branch (TEST_DATABASE_URL), never `main`.
"""

from pathlib import Path

import pytest

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.ports import KnowledgeRepository
from app.infra.kb_ingest import ingest
from app.infra.kb_repository import PostgresKnowledgeRepository

DOCS = {
    "tarifas.md": """---
id: TAR-001
tipo: tarifa
titulo: Tarifas generales
vigente_desde: 2026-01-01
ejemplo: true
---

## Limpieza dental

La limpieza dental con revisión cuesta 60 euros.

## Blanqueamiento

El blanqueamiento en clínica cuesta 280 euros.
""",
    "ortodoncia.md": """---
id: TRA-002
tipo: tratamiento
titulo: Ortodoncia
vigente_desde: 2026-01-01
---

## Duración del tratamiento

La duración habitual de la ortodoncia con brackets es de dieciocho meses.
""",
    "horario.md": """---
id: HOR-001
tipo: horario
titulo: Horario de apertura
vigente_desde: 2026-01-01
---

## Lunes a viernes

Abrimos de lunes a viernes de nueve a veinte horas.

## Sábados

Los sábados abrimos por la mañana.
""",
}


@pytest.fixture
def repo(test_db, tmp_path: Path) -> PostgresKnowledgeRepository:
    for name, text in DOCS.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    ingest(test_db, tmp_path)
    return PostgresKnowledgeRepository(test_db)


def _ids(fragments: list[Fragment]) -> list[tuple[str, str]]:
    return [(f.source_id, f.text.splitlines()[2]) for f in fragments]


def test_postgres_repository_implements_the_domain_port(repo):
    assert isinstance(repo, KnowledgeRepository)


def test_a_partially_overlapping_query_still_returns_the_fragment_in_the_top_k(repo):
    # Only "limpieza" appears in the document; "precio", "niños" and "sábado" do not
    # (or point elsewhere). An AND-combined query would return nothing.
    results = repo.search("precio de la limpieza para niños")

    assert ("TAR-001", "## Limpieza dental") in _ids(results)
    assert results[0].source_id == "TAR-001"


def test_returned_fragments_carry_metadata_and_a_normalized_descending_score(repo):
    results = repo.search("limpieza blanqueamiento euros")

    assert results
    first = results[0]
    assert first.titulo == "Tarifas generales"
    assert first.tipo == "tarifa"
    assert first.ejemplo is True
    assert first.vigente_desde.isoformat() == "2026-01-01"
    scores = [f.score for f in results]
    assert all(0 < s < 1 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_accented_and_unaccented_queries_return_the_same_fragments(repo):
    accented = repo.search("duración de la ortodoncia")
    unaccented = repo.search("duracion de la ortodoncia")

    assert accented
    assert _ids(accented) == _ids(unaccented)
    assert accented[0].source_id == "TRA-002"


def test_k_defaults_to_five_and_is_configurable(repo):
    # "abrimos" + "euros" + "limpieza" etc. match all five fragments.
    broad = "limpieza blanqueamiento ortodoncia abrimos"

    assert len(repo.search(broad)) == 5
    assert len(repo.search(broad, k=2)) == 2


@pytest.mark.parametrize(
    "query",
    [
        "limpieza: ¿cuánto cuesta?",
        "limpieza & blanqueamiento | !ortodoncia",
        "precio 'limpieza' \"dental\"",
        "limpieza:* <-> (brackets)",
        "!!! &&& ::: '''",
        "",
    ],
)
def test_special_characters_never_raise_and_return_a_ranked_list(repo, query):
    results = repo.search(query)

    assert isinstance(results, list)
    scores = [f.score for f in results]
    assert scores == sorted(scores, reverse=True)


def test_a_query_with_only_operators_returns_no_fragments(repo):
    assert repo.search("!!! &&& ::: '''") == []
