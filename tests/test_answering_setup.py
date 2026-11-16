"""SPEC-001 T0: setup for answer generation — dependencies, config placeholders and test doubles.

No test in this suite may call Gemini (plan: "Test environment and model usage").
"""

import importlib
import os
from datetime import date
from pathlib import Path

import pytest

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.ports import KnowledgeRepository
from tests.fakes import FakeKnowledgeRepository, FakeLanguageModel

ROOT = Path(__file__).resolve().parent.parent


def test_google_api_key_is_never_available_inside_tests():
    assert "GOOGLE_API_KEY" not in os.environ


@pytest.mark.parametrize("module", ["google.genai", "uvicorn"])
def test_new_dependencies_are_installed(module):
    importlib.import_module(module)


def test_env_example_documents_spec_001_settings_without_values():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    settings = dict(
        line.split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#")
    )
    for key in (
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
        "JUDGE_PROVIDER",
        "JUDGE_MODEL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_PRICE_INPUT_EUR_PER_MTOK",
        "LLM_PRICE_OUTPUT_EUR_PER_MTOK",
        "CONVERSATION_API_TOKEN",
        "API_HOST",
        "EVAL_MAX_RETRIES",
    ):
        assert key in settings, f"{key} missing from .env.example"
    # Secrets are placeholders only: never a real value in a committed file.
    for secret in ("GOOGLE_API_KEY", "CONVERSATION_API_TOKEN"):
        assert settings[secret].strip() == "", f"{secret} must be empty in .env.example"


def test_fake_language_model_returns_scripted_replies_in_order_and_records_calls():
    model = FakeLanguageModel(["primera", "segunda"])

    assert model.generate("prompt 1", timeout_seconds=4.0) == "primera"
    assert model.generate("prompt 2", timeout_seconds=4.0) == "segunda"
    assert model.calls == ["prompt 1", "prompt 2"]


def test_fake_language_model_raises_scripted_exceptions():
    model = FakeLanguageModel([TimeoutError("lento")])

    with pytest.raises(TimeoutError):
        model.generate("prompt", timeout_seconds=4.0)
    assert model.calls == ["prompt"]


def test_fake_language_model_fails_loudly_when_script_is_exhausted():
    model = FakeLanguageModel([])

    with pytest.raises(AssertionError, match="no scripted reply"):
        model.generate("prompt", timeout_seconds=4.0)


def _fragment(source_id: str, score: float) -> Fragment:
    return Fragment(
        text=f"texto {source_id}",
        titulo="Título",
        source_id=source_id,
        tipo="tarifa",
        vigente_desde=date(2026, 1, 1),
        ejemplo=True,
        score=score,
    )


def test_fake_knowledge_repository_implements_the_port_and_records_queries():
    repository = FakeKnowledgeRepository([_fragment("A", 0.2), _fragment("B", 0.5)])

    assert isinstance(repository, KnowledgeRepository)
    results = repository.search("¿cuánto cuesta?", k=1)
    assert [f.source_id for f in results] == ["B"]  # descending score, top k
    assert repository.queries == ["¿cuánto cuesta?"]
