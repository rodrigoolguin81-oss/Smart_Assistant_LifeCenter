"""T10 — `POST /internal/retrieval/query` (R3, R4, R6, R7, R8).

Integration test: the app reads its connection string from TEST_DATABASE_URL (Neon test
branch), never from DATABASE_URL (`main`).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.infra.kb_ingest import ingest
from app.main import create_app

KB_DIR = Path(__file__).resolve().parents[2] / "kb"
URL = "/internal/retrieval/query"


@pytest.fixture
def client(test_db, monkeypatch) -> TestClient:
    monkeypatch.delenv("RETRIEVAL_RELEVANCE_THRESHOLD", raising=False)
    ingest(test_db, KB_DIR)
    return TestClient(create_app(database_url_env="TEST_DATABASE_URL"))


def test_a_known_query_returns_200_with_the_contract_shape_and_cita(client):
    response = client.post(URL, json={"query": "cuánto cuesta una limpieza"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"fragments", "below_threshold"}
    assert body["below_threshold"] is False
    assert 1 <= len(body["fragments"]) <= 5

    top = body["fragments"][0]
    assert set(top) == {
        "text", "titulo", "source_id", "vigente_desde", "cita", "ejemplo", "score"
    }
    assert top["source_id"] == "TAR-001"
    assert top["titulo"] == "Tarifas generales de LifeCenter"
    assert top["vigente_desde"] == "2026-01-01"
    assert top["cita"] == "[TAR-001 | vigente desde 01/01/2026]"
    assert top["ejemplo"] is True
    assert 0 < top["score"] < 1


def test_k_defaults_to_5_and_is_caller_configurable(test_db, monkeypatch):
    # Isolate k from the relevance threshold: a many-term OR query dilutes ts_rank scores
    # (≈0.01–0.02 here), which would otherwise trip the 0.02 placeholder threshold.
    ingest(test_db, KB_DIR)
    monkeypatch.setenv("RETRIEVAL_RELEVANCE_THRESHOLD", "0")
    client = TestClient(create_app(database_url_env="TEST_DATABASE_URL"))
    broad = "limpieza blanqueamiento horario sábados agosto cuidados visita"

    assert len(client.post(URL, json={"query": broad}).json()["fragments"]) == 5
    assert len(client.post(URL, json={"query": broad, "k": 2}).json()["fragments"]) == 2


def test_a_query_with_no_match_returns_200_and_below_threshold(client):
    response = client.post(URL, json={"query": "aceptáis el seguro Sanitas para implantes"})

    assert response.status_code == 200
    assert response.json() == {"fragments": [], "below_threshold": True}


@pytest.mark.parametrize(
    "payload", [{}, {"query": "limpieza", "k": 0}, {"query": "limpieza", "k": "cinco"}]
)
def test_an_invalid_request_is_rejected_with_422(client, payload):
    assert client.post(URL, json=payload).status_code == 422


def test_the_relevance_threshold_is_configurable_via_environment(test_db, monkeypatch):
    ingest(test_db, KB_DIR)
    monkeypatch.setenv("RETRIEVAL_RELEVANCE_THRESHOLD", "0.99")
    strict = TestClient(create_app(database_url_env="TEST_DATABASE_URL"))

    response = strict.post(URL, json={"query": "cuánto cuesta una limpieza"})

    assert response.json() == {"fragments": [], "below_threshold": True}
