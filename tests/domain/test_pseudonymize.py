"""SPEC-001 T2: pseudonymize the question before it leaves the application (R4, RES-02)."""

import pytest

from app.domain.answering.pseudonymize import pseudonymize


@pytest.mark.parametrize(
    "phone",
    [
        "612345678",
        "612 34 56 78",
        "612 345 678",
        "612-345-678",
        "612.345.678",
        "+34 612 345 678",
        "+34612345678",
        "0034 612345678",
        "912 345 678",
        "711223344",
    ],
)
def test_spanish_phone_numbers_are_replaced(phone):
    assert pseudonymize(f"Llamadme al {phone}, gracias") == "Llamadme al [TELEFONO], gracias"


@pytest.mark.parametrize(
    "dni", ["12345678Z", "12345678-Z", "12345678 z", "X1234567L", "Y-1234567-X", "z1234567r"]
)
def test_dni_and_nie_are_replaced(dni):
    assert pseudonymize(f"Mi DNI es {dni}.") == "Mi DNI es [DNI]."


@pytest.mark.parametrize(
    "email", ["ana.garcia@gmail.com", "paciente+cita@clinica.example.es", "A_B-1@x.io"]
)
def test_emails_are_replaced(email):
    assert pseudonymize(f"Escribidme a {email} por favor") == "Escribidme a [EMAIL] por favor"


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Hola, me llamo Ana García y quiero una limpieza",
         "Hola, me llamo [NOMBRE] y quiero una limpieza"),
        ("Mi nombre es Luis, ¿cuánto cuesta un blanqueamiento?",
         "Mi nombre es [NOMBRE], ¿cuánto cuesta un blanqueamiento?"),
        ("Quiero una cita a nombre de Marta Ruiz", "Quiero una cita a nombre de [NOMBRE]"),
        ("Me llamo María de la Fuente López.", "Me llamo [NOMBRE]."),
        ("ME LLAMO José Ángel", "ME LLAMO [NOMBRE]"),
        # Patients often type in lowercase on Telegram.
        ("me llamo ana garcía y quiero cita", "me llamo [NOMBRE] y quiero cita"),
        ("mi nombre es luis", "mi nombre es [NOMBRE]"),
    ],
)
def test_names_after_explicit_introductions_are_replaced(question, expected):
    assert pseudonymize(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        # "soy X" is deliberately not a name pattern (clarifications Q5): it introduces
        # conditions the assistant needs.
        "soy alérgica a la anestesia, ¿qué me ponéis en la limpieza?",
        "Soy diabético, ¿puedo hacerme un blanqueamiento?",
        "Soy Ana",
        # An introduction followed by a common word is not a name.
        "Quiero una cita a nombre de mi hija",
        # No identifiers: unchanged, including prices, times, dates and years.
        "¿Cuánto cuesta una limpieza dental?",
        "¿La limpieza cuesta 60 € o 1.200 €?",
        "¿Abrís a las 9:00 el 15/12/2026?",
        "¿Tenéis cita en 2026 para 3 personas?",
    ],
)
def test_text_without_identifiers_is_returned_unchanged(question):
    assert pseudonymize(question) == question


def test_every_identifier_in_one_question_is_replaced():
    question = (
        "Me llamo Ana García, mi DNI es 12345678Z, mi móvil +34 612 345 678 "
        "y mi correo ana@gmail.com"
    )

    assert pseudonymize(question) == (
        "Me llamo [NOMBRE], mi DNI es [DNI], mi móvil [TELEFONO] y mi correo [EMAIL]"
    )
