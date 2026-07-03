import pytest

from backend.domain.fsm.ticket_fsm import (
    apply, can_transition, valid_triggers, InvalidTransitionError, TRANSITIONS,
)

# Las 16 transiciones de la matriz (data-model.md)
VALID_CASES = [
    ("nuevo", "assign_resolver", "contacto"),
    ("nuevo", "assign_qm", "pre_analisis"),
    ("pre_analisis", "assign_resolver", "contacto"),
    ("pre_analisis", "solicitud_informacion", "pendiente_usuario"),
    ("contacto", "confirmacion_atencion", "en_analisis"),
    ("en_analisis", "termina_analisis", "en_ejecucion"),
    ("en_analisis", "solicitud_informacion", "pendiente_usuario"),
    ("en_ejecucion", "solicitud_informacion", "pendiente_usuario"),
    ("en_ejecucion", "solicitud_cierre", "resuelto"),
    ("en_ejecucion", "enter_testing", "en_pruebas"),
    ("en_pruebas", "exit_testing", "en_ejecucion"),
    ("en_pruebas", "solicitud_cierre", "resuelto"),
    ("pendiente_usuario", "respuesta_usuario", "en_ejecucion"),
    ("resuelto", "reject_resolution", "en_ejecucion"),
    ("resuelto", "close", "cerrado"),
    ("nuevo", "cancel", "cancelado"),
]

INVALID_CASES = [
    ("nuevo", "solicitud_cierre"),        # no se puede resolver sin asignar
    ("nuevo", "confirmacion_atencion"),   # comentario de avance antes de asignar
    ("contacto", "termina_analisis"),
    ("cerrado", "assign_resolver"),       # estado final
    ("cerrado", "cancel"),                # final no cancelable
    ("cancelado", "respuesta_usuario"),
    ("resuelto", "solicitud_informacion"),
    ("en_analisis", "close"),
]


@pytest.mark.parametrize("source,trigger,expected", VALID_CASES)
def test_valid_transition(source, trigger, expected):
    assert can_transition(source, trigger)
    assert apply(source, trigger) == expected


@pytest.mark.parametrize("source,trigger", INVALID_CASES)
def test_invalid_transition_rejected(source, trigger):
    assert not can_transition(source, trigger)
    with pytest.raises(InvalidTransitionError) as exc:
        apply(source, trigger)
    assert exc.value.code == "invalid_transition"
    assert exc.value.status_code == 409
    assert "Acciones válidas" in exc.value.message


def test_cancel_available_from_all_non_final_states():
    for status in ("nuevo", "pre_analisis", "contacto", "en_analisis",
                   "en_ejecucion", "en_pruebas", "pendiente_usuario", "resuelto"):
        assert apply(status, "cancel") == "cancelado"


def test_final_states_have_no_triggers():
    assert valid_triggers("cerrado") == []
    assert valid_triggers("cancelado") == []


def test_matrix_has_exactly_expected_triggers():
    assert {t["trigger"] for t in TRANSITIONS} == {
        "assign_resolver", "assign_qm", "confirmacion_atencion", "termina_analisis",
        "solicitud_informacion", "solicitud_cierre", "respuesta_usuario",
        "enter_testing", "exit_testing", "reject_resolution", "close", "cancel",
    }
