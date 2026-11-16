"""SPEC-001 T1: fixed messages and the `Answer` model (R14, R15, R17)."""

import re

import pytest

from app.domain.answering import messages
from app.domain.answering.answer import Answer, Reason

CITATION = "[TAR-001 | vigente desde 01/01/2026]"
# Anything that looks like a figure or a citation must never reach a non-answer (R15).
FIGURE_OR_CITATION = re.compile(r"\d|€|\beuros?\b|\bEUR\b|\[|\]", re.IGNORECASE)

NON_ANSWERS = [
    Answer.abstention(Reason.BELOW_THRESHOLD),
    Answer.abstention(Reason.MODEL_ABSTAINED),
    Answer.abstention(Reason.VALIDATION_FAILED),
    Answer.llm_error("rate_limited"),
]


def test_fixed_texts_match_the_spec():
    assert messages.ABSTENTION_MESSAGE == (
        "Lo siento, no tengo esa información. ¿Quieres que pase tu consulta a recepción?"
    )
    assert messages.LLM_ERROR_MESSAGE == (
        "Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?"
    )
    assert messages.HANDOFF_LABEL == "Hablar con recepción"
    assert messages.PRICE_NOTICE == (
        "Los precios son «desde» y pueden variar tras una valoración previa en la clínica."
    )
    assert messages.EXAMPLE_NOTICE == (
        "Aviso: esta información es de ejemplo y no corresponde a datos reales de LifeCenter."
    )


@pytest.mark.parametrize("answer", NON_ANSWERS, ids=lambda a: a.reason.value)
def test_every_non_answer_offers_handoff_and_never_booking(answer):
    assert answer.abstained is True
    assert answer.offer_handoff is True
    assert answer.handoff_label == "Hablar con recepción"
    assert answer.offer_booking is False
    assert answer.citations == ()
    assert answer.ejemplo is False
    assert not FIGURE_OR_CITATION.search(answer.answer)


def test_abstentions_use_the_abstention_message():
    for reason in (Reason.BELOW_THRESHOLD, Reason.MODEL_ABSTAINED, Reason.VALIDATION_FAILED):
        answer = Answer.abstention(reason)
        assert answer.answer == messages.ABSTENTION_MESSAGE
        assert answer.reason is reason
        assert answer.error_kind is None


def test_llm_error_uses_its_own_message_and_keeps_the_error_kind():
    answer = Answer.llm_error("timeout")

    assert answer.answer == messages.LLM_ERROR_MESSAGE
    assert answer.reason is Reason.LLM_ERROR
    assert answer.error_kind == "timeout"


def test_abstention_rejects_reasons_that_are_not_abstentions():
    for reason in (Reason.ANSWERED, Reason.LLM_ERROR):
        with pytest.raises(ValueError):
            Answer.abstention(reason)


def test_answered_carries_citations_and_flags():
    answer = Answer.answered(
        f"La limpieza cuesta 60 € {CITATION}", citations=[CITATION], offer_booking=True, ejemplo=True
    )

    assert answer.abstained is False
    assert answer.reason is Reason.ANSWERED
    assert answer.offer_handoff is False
    assert answer.handoff_label is None
    assert answer.offer_booking is True
    assert answer.citations == (CITATION,)
    assert answer.ejemplo is True


def test_answered_requires_at_least_one_citation():
    with pytest.raises(ValueError):
        Answer.answered("Sin fuente.", citations=[], offer_booking=False, ejemplo=False)


def test_an_abstained_answer_can_never_offer_booking():
    """R14: the invariant holds even if someone bypasses the factories."""
    with pytest.raises(ValueError):
        Answer(
            answer=messages.ABSTENTION_MESSAGE,
            abstained=True,
            reason=Reason.VALIDATION_FAILED,
            offer_handoff=True,
            handoff_label=messages.HANDOFF_LABEL,
            offer_booking=True,
            citations=(),
            ejemplo=False,
        )


def test_an_abstained_answer_can_never_carry_citations():
    with pytest.raises(ValueError):
        Answer(
            answer=messages.ABSTENTION_MESSAGE,
            abstained=True,
            reason=Reason.MODEL_ABSTAINED,
            offer_handoff=True,
            handoff_label=messages.HANDOFF_LABEL,
            offer_booking=False,
            citations=(CITATION,),
            ejemplo=False,
        )
