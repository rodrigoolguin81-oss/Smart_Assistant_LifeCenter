"""eval_retrieval (NFR-05): Recall@5 of `KnowledgeRepository.search()` over annotated questions.

Offline, outside the production code path. Loads `kb/` into the Neon *test* branch, then checks,
for each question, whether its expected source `id` is among the top-5 fragments.

Usage:  python -m evals.eval_retrieval [--dataset PATH] [--kb-dir kb]
                                       [--database-url-env TEST_DATABASE_URL]
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import yaml
from dotenv import load_dotenv

from app.domain.retrieval.ports import KnowledgeRepository
from app.domain.retrieval.relevance import DEFAULT_RELEVANCE_THRESHOLD
from app.infra.kb_ingest import ingest
from app.infra.kb_repository import PostgresKnowledgeRepository

DATASET_PATH = Path(__file__).parent / "retrieval_dataset.yaml"
K = 5
TARGET_RECALL = 0.90


@dataclass(frozen=True)
class Question:
    question: str
    expected_id: str


@dataclass
class EvalReport:
    total: int
    hits: int
    misses: list[Question] = field(default_factory=list)
    below_threshold: list[Question] = field(default_factory=list)
    """Hits whose top score is under the relevance threshold: retrieve() would abstain."""

    @property
    def recall(self) -> float:
        return self.hits / self.total if self.total else 0.0


def load_dataset(path: Path) -> list[Question]:
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    questions = []
    for i, entry in enumerate(entries, 1):
        for key in ("question", "expected_id"):
            if not isinstance(entry, dict) or not entry.get(key):
                raise ValueError(f"{path.name}: entry {i} is missing '{key}'")
        questions.append(Question(str(entry["question"]), str(entry["expected_id"])))
    return questions


def run_eval(
    repository: KnowledgeRepository,
    dataset: list[Question],
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
) -> EvalReport:
    report = EvalReport(total=len(dataset), hits=0)
    for q in dataset:
        results = repository.search(q.question, k=K)
        if q.expected_id in {f.source_id for f in results[:K]}:
            report.hits += 1
            if (results[0].score or 0.0) < threshold:
                report.below_threshold.append(q)
        else:
            report.misses.append(q)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recall@5 del retrieval (NFR-05).")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--kb-dir", type=Path, default=Path("kb"))
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL")
    args = parser.parse_args(argv)

    load_dotenv(".env")
    url = os.environ.get(args.database_url_env)
    if not url:
        print(f"Error: la variable {args.database_url_env} no está definida.", file=sys.stderr)
        return 2
    # The eval re-ingests kb/ (a full replace), so it must never target main.
    if url in {os.environ.get("DATABASE_URL"), os.environ.get("DIRECT_URL")}:
        print("Error: el eval reemplaza kb_fragments; no se ejecuta contra main.", file=sys.stderr)
        return 2

    dataset = load_dataset(args.dataset)
    with psycopg.connect(url, autocommit=True) as conn:
        ingest(conn, args.kb_dir)
        report = run_eval(PostgresKnowledgeRepository(conn), dataset)

    print(f"Recall@{K}: {report.recall:.1%} ({report.hits}/{report.total}) "
          f"— objetivo ≥ {TARGET_RECALL:.0%}")
    for q in report.misses:
        print(f"  FALLO     [{q.expected_id}] {q.question}")
    print(f"Aciertos bajo el umbral de relevancia ({DEFAULT_RELEVANCE_THRESHOLD}): "
          f"{len(report.below_threshold)}/{report.hits}")
    for q in report.below_threshold:
        print(f"  ABSTENCIÓN [{q.expected_id}] {q.question}")
    return 0 if report.recall >= TARGET_RECALL else 1


if __name__ == "__main__":
    sys.exit(main())
