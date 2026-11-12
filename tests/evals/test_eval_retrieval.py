"""T11 — `eval_retrieval` dataset and Recall@5 script (NFR-05)."""

from datetime import date
from pathlib import Path

import pytest

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.kb_document import parse_kb_document
from evals.eval_retrieval import DATASET_PATH, Question, load_dataset, main, run_eval

KB_DIR = Path(__file__).resolve().parents[2] / "kb"


def _fragment(source_id: str, score: float = 0.05) -> Fragment:
    return Fragment(
        text="…",
        titulo="…",
        source_id=source_id,
        tipo="tarifa",
        vigente_desde=date(2026, 1, 1),
        ejemplo=True,
        score=score,
    )


class FakeRepository:
    def __init__(self, answers: dict[str, list[Fragment]]) -> None:
        self.answers = answers
        self.ks: list[int] = []

    def search(self, query: str, k: int = 5, today: date | None = None) -> list[Fragment]:
        self.ks.append(k)
        return self.answers[query][:k]


# --- recall computation (pure) -----------------------------------------------------------


def test_recall_counts_a_hit_when_the_expected_id_is_in_the_top_5():
    repo = FakeRepository(
        {
            "hit": [_fragment("HOR-001"), _fragment("TAR-001")],
            "miss": [_fragment("HOR-001")],
        }
    )
    dataset = [Question("hit", "TAR-001"), Question("miss", "TRA-001")]

    report = run_eval(repo, dataset)

    assert repo.ks == [5, 5]
    assert report.recall == 0.5
    assert [q.question for q in report.misses] == ["miss"]


def test_a_match_beyond_position_5_is_not_a_hit():
    six = [_fragment("HOR-001")] * 5 + [_fragment("TAR-001")]
    report = run_eval(FakeRepository({"q": six}), [Question("q", "TAR-001")])

    assert report.recall == 0.0


def test_hits_below_the_relevance_threshold_are_reported_separately():
    repo = FakeRepository({"q": [_fragment("TAR-001", score=0.01)]})

    report = run_eval(repo, [Question("q", "TAR-001")], threshold=0.02)

    assert report.recall == 1.0
    assert [q.question for q in report.below_threshold] == ["q"]


# --- dataset -----------------------------------------------------------------------------


def test_load_dataset_rejects_an_entry_without_expected_id(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- question: ¿Cuánto cuesta?\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected_id"):
        load_dataset(bad)


def test_interim_dataset_covers_every_example_document_with_known_ids():
    kb_ids = {
        parse_kb_document(p.read_text(encoding="utf-8"), source_name=p.name).id
        for p in KB_DIR.glob("*.md")
    }
    dataset = load_dataset(DATASET_PATH)

    assert len(dataset) >= 20
    assert {q.expected_id for q in dataset} == kb_ids
    assert any(len(q.question.split()) >= 12 for q in dataset), "include long questions"


# --- end to end over the Neon test branch ------------------------------------------------


def test_the_script_reports_recall_at_5_of_at_least_90_percent(test_db, capsys):
    exit_code = main(["--database-url-env", "TEST_DATABASE_URL"])

    out = capsys.readouterr().out
    assert "Recall@5" in out
    assert exit_code == 0, out


def test_the_script_refuses_to_run_against_main(capsys):
    assert main(["--database-url-env", "DIRECT_URL"]) == 2
    assert "main" in capsys.readouterr().err
