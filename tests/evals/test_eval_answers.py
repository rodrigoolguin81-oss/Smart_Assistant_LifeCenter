"""SPEC-011 E1 — the answer dataset (RE1–RE3) and the deterministic scoring (RE8–RE10).

No n8n, no Gemini, no network: the scoring runs on fixed results.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from evals.eval_answers import (
    DATASET_PATH,
    KB_DIR,
    Item,
    check_dataset,
    collect_runs,
    euro_amounts,
    load_dataset,
    load_kb,
    parse_flatted,
    read_execution,
    render_report,
    score,
    summarize,
)

KB = load_kb(KB_DIR)
CITA_TAR = "[TAR-001 | vigente desde 01/01/2026]"
CITA_TRA = "[TRA-001 | vigente desde 01/01/2026]"


def _answered(text: str, citations: list[str]) -> dict:
    return {"reason": "answered", "text": text, "citations": citations}


ANSWER_ITEM = Item("¿Cuánto cuesta una limpieza?", "answer", doc="TAR-001", fact="60 €")
ABSTAIN_ITEM = Item("¿Cuánto cuesta un implante?", "abstain")
URGENCY_ITEM = Item("Me duele mucho una muela", "urgency")


# --- dataset (RE1–RE3) -------------------------------------------------------------------


def test_the_dataset_has_73_items_with_the_agreed_split():
    items = load_dataset(DATASET_PATH)
    counts = {e: sum(i.expected == e for i in items) for e in ("answer", "abstain", "urgency")}
    assert len(items) == 73
    assert counts == {"answer": 20, "abstain": 50, "urgency": 3}
    assert len({i.question for i in items}) == 73


def test_the_dataset_keeps_the_19_abstention_questions_and_at_least_8_traps():
    items = load_dataset(DATASET_PATH)
    abstain = {i.question for i in items if i.expected == "abstain"}
    old = Path(DATASET_PATH).with_name("abstention_dataset.yaml").read_text(encoding="utf-8")
    old_questions = [
        line.split(":", 1)[1].strip() for line in old.splitlines() if line.startswith("- question:")
    ]
    assert len(old_questions) == 19
    assert set(old_questions) <= abstain
    traps = [i for i in items if i.expected == "abstain" and (i.note or "").startswith("trap:")]
    assert len(traps) >= 8
    kinds = {t.note for t in traps}
    assert {
        "trap: price not in kb",
        "trap: price that shares words with kb",
        "trap: medical question without symptoms",
        "trap: prompt injection",
    } <= kinds


def test_every_answer_item_names_a_kb_document_and_a_fact_found_in_it():
    items = load_dataset(DATASET_PATH)
    assert check_dataset(items, KB) == []
    answers = [i for i in items if i.expected == "answer"]
    assert all(i.doc and i.fact for i in answers)
    assert {i.doc for i in answers} == {"HOR-001", "TAR-001", "TRA-001"}
    assert all(i.doc is None and i.fact is None for i in items if i.expected != "answer")


def test_check_dataset_reports_an_unknown_doc_and_a_fact_not_in_the_document():
    bad = [
        Item("a", "answer", doc="XYZ-001", fact="60 €"),
        Item("b", "answer", doc="TAR-001", fact="99 €"),
        Item("c", "answer"),
    ]
    errors = check_dataset(bad, KB)
    assert len(errors) == 3


def test_load_dataset_rejects_an_unknown_expected_value(tmp_path):
    path = tmp_path / "d.yaml"
    path.write_text('- question: "x"\n  expected: maybe\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataset(path)


# --- € figures ---------------------------------------------------------------------------


def test_euro_amounts_reads_the_usual_spellings():
    assert euro_amounts("cuesta 60 € y 280€, o 30 euros; también 1.200,50 €") == {
        6000,
        28000,
        3000,
        120050,
    }
    assert euro_amounts("abre a las 9:00, dura 45 minutos") == set()


# --- scoring rules (RE8), a true and a false case each --------------------------------------


def test_an_answer_is_correct_when_it_cites_the_doc_and_holds_the_fact():
    result = _answered(f"La limpieza cuesta 60 € {CITA_TAR}.", [CITA_TAR])
    assert score(ANSWER_ITEM, result, KB).outcome == "correct"


def test_an_answer_without_the_fact_or_the_doc_is_wrong_not_correct():
    no_fact = _answered(f"La limpieza la hace la higienista {CITA_TAR}.", [CITA_TAR])
    other_doc = _answered(f"La limpieza elimina el sarro {CITA_TRA}. 60 € no.", [CITA_TRA])
    assert score(ANSWER_ITEM, no_fact, KB).outcome == "wrong"
    s = score(ANSWER_ITEM, other_doc, KB)
    assert s.outcome in {"wrong", "invented"}
    assert s.outcome != "correct"


def test_the_fact_is_compared_without_case_accents_or_spacing():
    item = Item("q", "answer", doc="TRA-001", fact="preparacion")
    result = _answered(f"No necesitas ninguna PREPARACIÓN especial {CITA_TRA}.", [CITA_TRA])
    assert score(item, result, KB).outcome == "correct"
    euro = _answered(f"Cuesta 60€ {CITA_TAR}.", [CITA_TAR])
    assert score(ANSWER_ITEM, euro, KB).outcome == "correct"


@pytest.mark.parametrize("reason", ["below_threshold", "model_abstained", "validation_failed"])
def test_an_abstain_item_that_abstains_is_correct(reason):
    assert score(ABSTAIN_ITEM, {"reason": reason, "text": "Lo siento…"}, KB).outcome == "correct"


def test_an_abstain_item_that_is_answered_is_invented():
    result = _answered(f"La limpieza cuesta 60 € {CITA_TAR}.", [CITA_TAR])
    s = score(ABSTAIN_ITEM, result, KB)
    assert s.outcome == "invented"
    assert s.rule


def test_an_answer_item_that_abstains_is_a_false_abstention():
    s = score(ANSWER_ITEM, {"reason": "below_threshold", "text": "Lo siento…"}, KB)
    assert s.outcome == "false_abstention"
    assert score(ANSWER_ITEM, _answered(f"60 € {CITA_TAR}", [CITA_TAR]), KB).outcome != (
        "false_abstention"
    )


def test_a_citation_that_is_not_a_kb_id_is_invented():
    cita = "[TAR-999 | vigente desde 01/01/2026]"
    s = score(ANSWER_ITEM, _answered(f"60 € {CITA_TAR} {cita}", [CITA_TAR, cita]), KB)
    assert s.outcome == "invented"


def test_a_euro_figure_not_in_the_cited_document_is_invented():
    bad = _answered(f"La limpieza cuesta 65 € {CITA_TAR}. 60 €", [CITA_TAR])
    good = _answered(f"La limpieza cuesta 60 € y la panorámica 30 € {CITA_TAR}.", [CITA_TAR])
    assert score(ANSWER_ITEM, bad, KB).outcome == "invented"
    assert score(ANSWER_ITEM, good, KB).outcome == "correct"


def test_urgency_is_correct_only_for_urgency_items():
    urgency = {"reason": "urgency", "text": "No puedo valorar síntomas por aquí…"}
    assert score(URGENCY_ITEM, urgency, KB).outcome == "correct"
    assert score(ABSTAIN_ITEM, urgency, KB).outcome == "wrong"
    abstained = {"reason": "below_threshold", "text": "Lo siento…"}
    assert score(URGENCY_ITEM, abstained, KB).outcome == "wrong"


def test_llm_error_is_set_apart():
    s = score(ABSTAIN_ITEM, {"reason": "llm_error", "text": "Ahora mismo no puedo…"}, KB)
    assert s.outcome == "llm_error"
    assert score(ABSTAIN_ITEM, None, KB).outcome == "wrong"


# --- metrics (RE9) -----------------------------------------------------------------------


def test_summarize_computes_the_metrics_and_leaves_llm_error_out():
    answered = _answered(f"La limpieza cuesta 60 € {CITA_TAR}.", [CITA_TAR])
    abstained = {"reason": "below_threshold", "text": "Lo siento…"}
    llm_error = {"reason": "llm_error", "text": "Ahora mismo…"}
    rows = [
        (ANSWER_ITEM, answered),
        (ANSWER_ITEM, abstained),
        (ABSTAIN_ITEM, abstained),
        (ABSTAIN_ITEM, answered),
        (ABSTAIN_ITEM, llm_error),
        (URGENCY_ITEM, {"reason": "urgency", "text": "…"}),
    ]
    m = summarize([(item, result, score(item, result, KB)) for item, result in rows])
    assert m.abstain_scored == 2 and m.abstain_correct == 1
    assert m.nfr03 == pytest.approx(0.5)
    assert m.answer_total == 2 and m.answer_correct == 1
    assert m.false_abstentions == 1
    assert m.invented == 1
    assert m.llm_errors == 1
    assert m.urgency_correct == 1 and m.urgency_total == 1
    assert m.euro_answers == 2 and m.euro_answers_with_valid_id == 2
    assert m.nfr06 == pytest.approx(1.0)


# --- n8n executions, read-only -----------------------------------------------------------


def test_parse_flatted_revives_shared_strings_and_nested_objects():
    raw = '[{"a":"1","b":"2","n":3},"x",[1,"1","3"],{"c":"1"}]'
    assert parse_flatted(raw) == {"a": "x", "b": [1, "x", {"c": "x"}], "n": 3}


def _flatted(obj) -> str:
    """A minimal flatted encoder for the fixtures (strings and objects moved to the table)."""
    table: list = []

    def put(value):
        if isinstance(value, str):
            table.append(value)
            return str(len(table) - 1)
        if isinstance(value, dict):
            index = len(table)
            table.append(None)
            table[index] = {k: put(v) for k, v in value.items()}
            return str(index)
        if isinstance(value, list):
            index = len(table)
            table.append(None)
            table[index] = [put(v) for v in value]
            return str(index)
        return value

    put(obj)
    return json.dumps(table)


def _execution_data(question: str, result: dict, pinned=("Recibir pregunta",), gemini_runs=1):
    item = lambda j: {"data": {"main": [[{"json": j}]]}}  # noqa: E731
    run_data = {
        "Recibir pregunta": [item({"question": question})],
        "Resultado": [item(result)],
    }
    if gemini_runs:
        run_data["Gemini"] = [item({"responseId": "r"}) for _ in range(gemini_runs)]
    return {
        "resultData": {
            "runData": run_data,
            "pinData": {name: [{"json": {"question": question}}] for name in pinned},
        }
    }


def _db(tmp_path, rows) -> Path:
    path = tmp_path / "database.sqlite"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE execution_entity (id INTEGER, workflowId TEXT, mode TEXT, status TEXT,"
        " startedAt TEXT, stoppedAt TEXT)"
    )
    con.execute("CREATE TABLE execution_data (executionId INTEGER, data TEXT)")
    for i, (wf, started, data) in enumerate(rows, start=500):
        con.execute(
            "INSERT INTO execution_entity VALUES (?,?,?,?,?,?)",
            (i, wf, "manual", "success", started, started),
        )
        con.execute("INSERT INTO execution_data VALUES (?,?)", (i, _flatted(data)))
    con.commit()
    con.close()
    return path


def test_read_execution_returns_the_result_the_question_and_what_was_pinned(tmp_path):
    result = {"reason": "answered", "text": "t", "citations": []}
    db = _db(tmp_path, [("B", "2026-11-28 12:00:00.000", _execution_data("q1", result))])
    run = read_execution(db, 500)
    assert run.question == "q1"
    assert run.result == result
    assert run.pinned == ["Recibir pregunta"]
    assert run.gemini_runs == 1
    assert run.workflow_id == "B"


def test_collect_runs_maps_executions_to_items_by_question_in_order(tmp_path):
    items = [Item("q1", "abstain"), Item("q2", "abstain")]
    r = {"reason": "below_threshold", "text": "t"}
    db = _db(
        tmp_path,
        [
            ("B", "2026-11-28 12:00:00.000", _execution_data("q1", r)),
            ("A", "2026-11-28 12:00:05.000", _execution_data("q2", r)),
            ("B", "2026-11-28 12:00:10.000", _execution_data("q2", r)),
            ("B", "2026-11-28 12:00:20.000", _execution_data("q1", r)),
        ],
    )
    runs = collect_runs(db, "B", after_id=499, items=items)
    assert runs == {1: [500, 503], 2: [502]}


# --- report (RE11, RE12) -----------------------------------------------------------------


def test_the_report_holds_the_metrics_every_failure_with_its_text_and_the_execution_ids():
    answered = _answered(f"El implante cuesta 60 € {CITA_TAR}.", [CITA_TAR])
    abstained = {"reason": "below_threshold", "text": "Lo siento…"}
    scored = [
        (ABSTAIN_ITEM, answered, score(ABSTAIN_ITEM, answered, KB)),
        (ANSWER_ITEM, abstained, score(ANSWER_ITEM, abstained, KB)),
    ]
    report = render_report(
        scored,
        runs={1: [601], 2: [602]},
        kb_hash="abc123",
        gemini_calls=1,
        run_date="2026-11-28",
        notes=[],
    )
    assert "NFR-03" in report and "NFR-06" in report
    assert "El implante cuesta 60 €" in report
    assert ABSTAIN_ITEM.question in report and ANSWER_ITEM.question in report
    assert "601" in report and "602" in report
    assert "abc123" in report
    assert "30 días" in report
