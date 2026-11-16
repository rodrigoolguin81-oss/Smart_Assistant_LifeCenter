"""Fixed patient-facing texts (SPEC-001). Kept in one place so they can change without touching logic.

PRICE_NOTICE and EXAMPLE_NOTICE are PROVISIONAL, pending CONF-002 (decided by Prince Calderon);
see specs/002-answer-generation/clarifications.md (Assumptions) and spec R12/R13.
"""

ABSTENTION_MESSAGE = (
    "Lo siento, no tengo esa información. ¿Quieres que pase tu consulta a recepción?"
)
"""R7, R9, R11 — clarifications Q13."""

LLM_ERROR_MESSAGE = "Ahora mismo no puedo responder. ¿Quieres que pase tu consulta a recepción?"
"""R16 — clarifications Q12."""

HANDOFF_LABEL = "Hablar con recepción"
"""R15 — button rendered by n8n (clarifications Q7)."""

PRICE_NOTICE = (
    "Los precios son «desde» y pueden variar tras una valoración previa en la clínica."
)
"""R12 — PROVISIONAL, pending CONF-002."""

EXAMPLE_NOTICE = (
    "Aviso: esta información es de ejemplo y no corresponde a datos reales de LifeCenter."
)
"""R13 — PROVISIONAL, pending CONF-002."""
