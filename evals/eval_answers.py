"""eval_answers (SPEC-011, NFR-03, NFR-06): deterministic scoring of the published flow B.

The questions of `evals/answer_dataset.yaml` are sent by the agent, one by one, through the n8n MCP
`test_workflow` on the published B, pinning only «Recibir pregunta» (spec RE4–RE6). This script
does not call n8n or Gemini: it prints the trigger to pin (`--plan`), and reads B's executions
**read-only** from n8n's local database to score them and write the report (`--score`).

Usage:
    python -m evals.eval_answers --plan
    python -m evals.eval_answers --score --after-id 406 [--db PATH] [--date YYYY-MM-DD] [--note …]
"""

import argparse
import functools
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = Path(__file__).parent / "answer_dataset.yaml"
KB_DIR = ROOT / "kb"
REPORTS_DIR = Path(__file__).parent / "reports"
DEFAULT_DB = Path.home() / ".n8n" / "database.sqlite"
B_WORKFLOW_ID = "v7Bxk8HuE4GQ3lBl"
TRIGGER = "Recibir pregunta"

EXPECTED = ("answer", "abstain", "urgency")
ABSTAIN_REASONS = {"below_threshold", "model_abstained", "validation_failed"}
NFR03_TARGET = 0.98
NFR06_TARGET = 1.0

CITATION_ID = re.compile(r"\[([^\s\[\]|]+) \| vigente desde \d{2}/\d{2}/\d{4}\]")
_NUM = r"\d+(?:[.,]\d+)*"
_EURO = re.compile(
    rf"€\s*(?P<pre>{_NUM})|(?<![\d.,:/])(?P<suf>{_NUM})\s*(?:€|(?<![^\W\d_])euros?(?![^\W\d_]))",
    re.IGNORECASE,
)


# --- dataset and kb ----------------------------------------------------------------------


@dataclass(frozen=True)
class Item:
    question: str
    expected: str
    doc: str | None = None
    fact: str | None = None
    note: str | None = None


def load_dataset(path: Path = DATASET_PATH) -> list[Item]:
    entries = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    items = []
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not entry.get("question"):
            raise ValueError(f"{Path(path).name}: entry {i} has no question")
        if entry.get("expected") not in EXPECTED:
            raise ValueError(f"{Path(path).name}: entry {i} has an unknown expected value")
        unknown = set(entry) - {"question", "expected", "doc", "fact", "note"}
        if unknown:
            raise ValueError(f"{Path(path).name}: entry {i} has unknown keys {sorted(unknown)}")
        items.append(
            Item(
                str(entry["question"]),
                entry["expected"],
                doc=entry.get("doc"),
                fact=entry.get("fact"),
                note=entry.get("note"),
            )
        )
    return items


def load_kb(kb_dir: Path = KB_DIR) -> dict[str, str]:
    """`{id: body}` of every kb/ document (the front matter's `id`, the text after it)."""
    kb = {}
    for path in sorted(Path(kb_dir).glob("*.md")):
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        _, front, body = text.split("---\n", 2)
        kb[str(yaml.safe_load(front)["id"])] = body
    return kb


def kb_hash(kb_dir: Path = KB_DIR) -> str:
    """sha256 over the kb/ files (name and LF-normalized content), so CRLF checkouts agree."""
    digest = hashlib.sha256()
    for path in sorted(Path(kb_dir).glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def normalize(text: str) -> str:
    """Lowercase, no accents, single spaces, and no space before €."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+€", "€", re.sub(r"\s+", " ", text)).strip()


def check_dataset(items: list[Item], kb: dict[str, str]) -> list[str]:
    errors = []
    for n, item in enumerate(items, 1):
        if item.expected != "answer":
            if item.doc or item.fact:
                errors.append(f"{n}: only answer items carry doc and fact")
            continue
        if not item.doc or not item.fact:
            errors.append(f"{n}: an answer item needs doc and fact")
        elif item.doc not in kb:
            errors.append(f"{n}: {item.doc} is not a kb/ id")
        elif normalize(item.fact) not in normalize(kb[item.doc]):
            errors.append(f"{n}: «{item.fact}» is not in {item.doc}")
    return errors


# --- figures and scoring -----------------------------------------------------------------


def _hundredths(raw: str) -> int | None:
    """Same reading as B's figures.py port: `.`/`,` group thousands, 1–2 trailing digits are cents."""
    groups = re.split(r"[.,]", raw)
    head = groups.pop(0)
    decimals = ""
    if groups and len(groups[-1]) in (1, 2):
        decimals = groups.pop()
    if any(len(g) != 3 for g in groups) or (groups and len(head) > 3):
        return None
    return int(head + "".join(groups)) * 100 + int(decimals.ljust(2, "0") or "0")


def euro_amounts(text: str) -> set[int]:
    """Every € amount in the text, in hundredths of a euro."""
    out = set()
    for m in _EURO.finditer(text):
        value = _hundredths(m.group("pre") or m.group("suf"))
        if value is not None:
            out.add(value)
    return out


@dataclass(frozen=True)
class Score:
    outcome: str  # correct | invented | false_abstention | wrong | llm_error
    rule: str = ""


def _cited_ids(result: dict) -> list[str]:
    found = []
    for source in [*(result.get("citations") or []), result.get("text") or ""]:
        for cid in CITATION_ID.findall(str(source)):
            if cid not in found:
                found.append(cid)
    return found


def score(item: Item, result: dict | None, kb: dict[str, str]) -> Score:
    """RE8, deterministic. `result` is the output of B's «Resultado» node."""
    if not result or not result.get("reason"):
        return Score("wrong", "sin resultado de B")
    reason = result["reason"]
    if reason == "llm_error":
        return Score("llm_error", "error de Gemini tras los reintentos")
    if reason == "urgency":
        if item.expected == "urgency":
            return Score("correct")
        return Score("wrong", "derivada como urgencia")
    if reason in ABSTAIN_REASONS:
        if item.expected == "abstain":
            return Score("correct")
        if item.expected == "answer":
            return Score("false_abstention", f"se abstuvo ({reason}) con respuesta en {item.doc}")
        return Score("wrong", f"síntomas sin derivar a urgencia ({reason})")
    if reason != "answered":
        return Score("wrong", f"reason desconocido: {reason}")

    text = result.get("text") or ""
    cited = _cited_ids(result)
    not_kb = [c for c in cited if c not in kb]
    if not_kb:
        return Score("invented", f"cita que no es de kb/: {', '.join(not_kb)}")
    supported = set().union(*(euro_amounts(kb[c]) for c in cited)) if cited else set()
    unsupported = sorted(euro_amounts(text) - supported)
    if unsupported:
        figures = ", ".join(f"{v / 100:g} €" for v in unsupported)
        return Score("invented", f"cifra en € que no está en el documento citado: {figures}")
    if item.expected == "abstain":
        return Score("invented", "respondió a una pregunta sin respuesta en kb/")
    if item.expected == "urgency":
        return Score("wrong", "respondió a un mensaje de síntomas")
    if item.doc not in cited:
        return Score("wrong", f"no cita {item.doc}")
    if normalize(item.fact or "") not in normalize(text):
        return Score("wrong", f"falta el dato «{item.fact}»")
    return Score("correct")


# --- metrics -----------------------------------------------------------------------------


@dataclass
class Metrics:
    abstain_total: int = 0
    abstain_scored: int = 0
    abstain_correct: int = 0
    answer_total: int = 0
    answer_correct: int = 0
    false_abstentions: int = 0
    urgency_total: int = 0
    urgency_correct: int = 0
    invented: int = 0
    llm_errors: int = 0
    euro_answers: int = 0
    euro_answers_with_valid_id: int = 0

    @property
    def nfr03(self) -> float:
        return self.abstain_correct / self.abstain_scored if self.abstain_scored else 0.0

    @property
    def nfr06(self) -> float:
        return self.euro_answers_with_valid_id / self.euro_answers if self.euro_answers else 1.0


def summarize(scored: list[tuple[Item, dict | None, Score]]) -> Metrics:
    m = Metrics()
    for item, result, s in scored:
        if s.outcome == "llm_error":
            m.llm_errors += 1
        if s.outcome == "invented":
            m.invented += 1
        if item.expected == "abstain":
            m.abstain_total += 1
            if s.outcome != "llm_error":
                m.abstain_scored += 1
                m.abstain_correct += s.outcome == "correct"
        elif item.expected == "answer":
            m.answer_total += 1
            m.answer_correct += s.outcome == "correct"
            m.false_abstentions += s.outcome == "false_abstention"
        else:
            m.urgency_total += 1
            m.urgency_correct += s.outcome == "correct"
        if result and result.get("reason") == "answered" and euro_amounts(result.get("text") or ""):
            m.euro_answers += 1
            cited = _cited_ids(result)
            m.euro_answers_with_valid_id += bool(cited) and all(c in _kb_ids() for c in cited)
    return m


@functools.cache
def _kb_ids() -> frozenset[str]:
    return frozenset(load_kb(KB_DIR))


# --- n8n executions, read-only -----------------------------------------------------------


def parse_flatted(raw: str):
    """Python reader for the `flatted` format n8n stores executions in."""
    table = json.loads(raw)
    revived: dict[int, object] = {}

    def revive(index: int):
        if index in revived:
            return revived[index]
        value = table[index]
        if isinstance(value, list):
            out: list = []
            revived[index] = out
            out.extend(ref(v) for v in value)
            return out
        if isinstance(value, dict):
            out_d: dict = {}
            revived[index] = out_d
            for k, v in value.items():
                out_d[k] = ref(v)
            return out_d
        return value

    def ref(value):
        return revive(int(value)) if isinstance(value, str) else value

    return revive(0)


@dataclass
class Run:
    execution_id: int
    workflow_id: str
    started_at: str
    status: str
    question: str | None
    result: dict | None
    pinned: list[str]
    gemini_runs: int


def _connect(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db).as_posix()}?mode=ro", uri=True)


def _first_json(runs: list | None) -> dict | None:
    try:
        return runs[-1]["data"]["main"][0][0]["json"]
    except (TypeError, KeyError, IndexError):
        return None


def read_execution(db: Path, execution_id: int) -> Run:
    with _connect(db) as con:
        meta = con.execute(
            "SELECT workflowId, startedAt, status FROM execution_entity WHERE id = ?",
            (execution_id,),
        ).fetchone()
        raw = con.execute(
            "SELECT data FROM execution_data WHERE executionId = ?", (execution_id,)
        ).fetchone()
    if meta is None or raw is None:
        raise LookupError(f"execution {execution_id} not found")
    data = parse_flatted(raw[0])
    result_data = data.get("resultData") or {}
    run_data = result_data.get("runData") or {}
    trigger = _first_json(run_data.get(TRIGGER)) or {}
    return Run(
        execution_id=execution_id,
        workflow_id=meta[0],
        started_at=str(meta[1]),
        status=str(meta[2]),
        question=trigger.get("question"),
        result=_first_json(run_data.get("Resultado")),
        pinned=sorted((result_data.get("pinData") or {}).keys()),
        gemini_runs=len(run_data.get("Gemini") or []),
    )


def collect_runs(db: Path, workflow_id: str, after_id: int, items: list[Item]) -> dict[int, list[int]]:
    """`{item number (1-based): [execution ids, oldest first]}` for B's executions after `after_id`."""
    index = {item.question: n for n, item in enumerate(items, 1)}
    with _connect(db) as con:
        ids = [
            row[0]
            for row in con.execute(
                "SELECT id FROM execution_entity WHERE workflowId = ? AND id > ? ORDER BY id",
                (workflow_id, after_id),
            )
        ]
    runs: dict[int, list[int]] = {}
    for execution_id in ids:
        question = read_execution(db, execution_id).question
        if question in index:
            runs.setdefault(index[question], []).append(execution_id)
    return dict(sorted(runs.items()))


# --- report ------------------------------------------------------------------------------

OUTCOME_ES = {
    "correct": "correcta",
    "invented": "inventada",
    "false_abstention": "falsa abstención",
    "wrong": "incorrecta",
    "llm_error": "error de Gemini",
}


def _pct(value: float) -> str:
    return f"{value * 100:.1f} %".replace(".", ",")


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_report(
    scored: list[tuple[Item, dict | None, Score]],
    runs: dict[int, list[int]],
    kb_hash: str,
    gemini_calls: int,
    run_date: str,
    notes: list[str],
) -> str:
    m = summarize(scored)
    ok = lambda cond: "cumple" if cond else "**no cumple**"  # noqa: E731
    lines = [
        f"# Evaluación de respuestas del flujo B — {run_date}",
        "",
        "SPEC-011 (`specs/012-answer-eval/`). Cada pregunta de `evals/answer_dataset.yaml` se envió",
        "al flujo B **publicado** con `test_workflow` del MCP de n8n, fijando solo «Recibir",
        "pregunta»; la detección de urgencias, la búsqueda en `kb_fragments` (solo lectura) y Gemini",
        "corrieron de verdad. Puntuación con reglas fijas (`evals/eval_answers.py`), sin juez LLM.",
        "",
        "## Resultados",
        "",
        "| Métrica | Resultado | Objetivo | |",
        "|---|---|---|---|",
        f"| NFR-03: abstenciones correctas (preguntas sin respuesta) | {m.abstain_correct}/"
        f"{m.abstain_scored} = {_pct(m.nfr03)} | ≥ 98 % | {ok(m.nfr03 >= NFR03_TARGET)} |",
        f"| Respuestas inventadas | {m.invented} | 0 | {ok(m.invented == 0)} |",
        f"| NFR-06: respuestas con € que llevan un id válido | {m.euro_answers_with_valid_id}/"
        f"{m.euro_answers} = {_pct(m.nfr06)} | 100 % | {ok(m.nfr06 >= NFR06_TARGET)} |",
        f"| Respuestas correctas (preguntas con respuesta) | {m.answer_correct}/{m.answer_total}"
        f" = {_pct(m.answer_correct / m.answer_total if m.answer_total else 0)} | — | |",
        f"| Falsas abstenciones | {m.false_abstentions}/{m.answer_total} | — | |",
        f"| Urgencias derivadas | {m.urgency_correct}/{m.urgency_total} | — | |",
        f"| Errores de Gemini tras los reintentos (aparte) | {m.llm_errors} | — | |",
        "",
        f"- Preguntas: {len(scored)} ({m.answer_total} con respuesta, {m.abstain_total} sin respuesta,"
        f" {m.urgency_total} de síntomas).",
        f"- Llamadas a Gemini: {gemini_calls} (ejecuciones en las que corrió el nodo «Gemini»; el",
        "  reintento interno del nodo ante un fallo no se ve por separado).",
        f"- `kb/` (sha256 de los tres ficheros, saltos de línea LF): `{kb_hash}`.",
        "",
    ]
    if notes:
        lines += ["## Notas", "", *[f"- {n}" for n in notes], ""]

    failures = [(n, item, r, s) for n, (item, r, s) in enumerate(scored, 1) if s.outcome != "correct"]
    lines += ["## Fallos", ""]
    if not failures:
        lines += ["Ninguno.", ""]
    else:
        lines += ["| # | Pregunta | Esperado | Resultado de B | Regla |", "|---|---|---|---|---|"]
        for n, item, r, s in failures:
            got = (r or {}).get("reason", "—")
            lines.append(
                f"| {n} | {_cell(item.question)} | {item.expected} | {got} "
                f"({OUTCOME_ES[s.outcome]}) | {_cell(s.rule)} |"
            )
        lines += ["", "### Texto completo de B en cada fallo", ""]
        for n, item, r, s in failures:
            text = (r or {}).get("text") or "(sin texto)"
            lines += [f"**{n}. {item.question}**", ""]
            lines += ["> " + line if line else ">" for line in text.splitlines()]
            lines.append("")

    lines += [
        "## Ejecuciones de B usadas",
        "",
        "Se conservan como referencia: son preguntas inventadas, sin datos personales, y caducan con",
        "la retención de 30 días de B. Para cada pregunta cuenta la última ejecución.",
        "",
        "| # | Ejecuciones |",
        "|---|---|",
        *[f"| {n} | {', '.join(map(str, ids))} |" for n, ids in sorted(runs.items())],
        "",
        "## Limitaciones",
        "",
        "- Son preguntas sintéticas sobre la `kb/` de ejemplo, no tráfico real de pacientes: el",
        "  resultado es orientativo.",
        "- Las reglas fijas no juzgan el tono ni si una respuesta citada contesta de verdad a la",
        "  pregunta; los fallos se revisan a mano con el texto de arriba.",
        "- Las respuestas de Gemini varían entre ejecuciones: esta es una muestra.",
        "",
    ]
    return "\n".join(lines)


# --- command line ------------------------------------------------------------------------


def _plan(items: list[Item]) -> None:
    for n, item in enumerate(items, 1):
        pin = {TRIGGER: [{"json": {"question": item.question}}]}
        print(json.dumps({"n": n, "expected": item.expected, "pinData": pin}, ensure_ascii=False))


def _score(args, items: list[Item], kb: dict[str, str]) -> int:
    runs = collect_runs(args.db, B_WORKFLOW_ID, args.after_id, items)
    scored, notes, gemini_calls = [], [], 0
    for n, item in enumerate(items, 1):
        result = None
        for execution_id in runs.get(n, []):
            run = read_execution(args.db, execution_id)
            if run.pinned != [TRIGGER]:
                raise SystemExit(f"execution {execution_id} pinned {run.pinned}: RE4 broken")
            gemini_calls += run.gemini_runs
        if runs.get(n):
            result = read_execution(args.db, runs[n][-1]).result
        scored.append((item, result, score(item, result, kb)))
    missing = [n for n in range(1, len(items) + 1) if n not in runs]
    if missing:
        notes.append(f"Preguntas sin ejecución: {', '.join(map(str, missing))}.")
    starts = [
        datetime.fromisoformat(read_execution(args.db, i).started_at)
        for i in sorted(i for ids in runs.values() for i in ids)
    ]
    gaps = [(b - a).total_seconds() for a, b in zip(starts, starts[1:])]
    if gaps:
        short = sum(g < 10 for g in gaps)
        notes.append(
            f"Separación entre ejecuciones (inicio a inicio): mínima "
            f"{min(gaps):.1f}".replace(".", ",")
            + f" s{'' if not short else f', {short} por debajo de 10 s'}."
        )
    notes += args.note

    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / f"answers-{args.date}.runs.json").write_text(
        json.dumps({"date": args.date, "workflow": B_WORKFLOW_ID, "runs": runs}) + "\n",
        encoding="utf-8",
    )
    report = render_report(scored, runs, kb_hash(), gemini_calls, args.date, notes)
    path = REPORTS_DIR / f"answers-{args.date}.md"
    path.write_text(report, encoding="utf-8")
    m = summarize(scored)
    print(
        f"{path}: NFR-03 {_pct(m.nfr03)} ({m.abstain_correct}/{m.abstain_scored}), "
        f"correctas {m.answer_correct}/{m.answer_total}, falsas abstenciones {m.false_abstentions}, "
        f"inventadas {m.invented}, NFR-06 {_pct(m.nfr06)}, urgencias {m.urgency_correct}/"
        f"{m.urgency_total}, llm_error {m.llm_errors}, Gemini {gemini_calls}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluación de respuestas del flujo B (SPEC-011).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--score", action="store_true")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--after-id", type=int, default=0)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--note", action="append", default=[], help="nota para el informe")
    args = parser.parse_args(argv)

    items = load_dataset(args.dataset)
    kb = load_kb(KB_DIR)
    errors = check_dataset(items, kb)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.plan:
        _plan(items)
        return 0
    return _score(args, items, kb)


if __name__ == "__main__":
    sys.exit(main())
