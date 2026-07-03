"""Máquina de estados del ticket (matriz oficial: docs/Regla de actividad de estados.xlsx).

Única fuente de verdad de las transiciones (FR-008). En Fase 1 los triggers se disparan
por acciones manuales; en Fase 6 el motor de automatización agregará callbacks sobre esta
misma definición. Sin imports de Flask/SQLAlchemy (Capa 1).
"""
from transitions import Machine, MachineError

from backend.domain.entities.ticket import STATUSES, FINAL_STATUSES
from backend.domain.errors import DomainError


class InvalidTransitionError(DomainError):
    default_status_code = 409


# trigger -> lista de (source, dest). Fuente: data-model.md tabla FSM (16 transiciones).
TRANSITIONS: list[dict] = [
    # Triage Push (US2)
    {"trigger": "assign_resolver", "source": ["nuevo", "pre_analisis"], "dest": "contacto"},
    {"trigger": "assign_qm", "source": "nuevo", "dest": "pre_analisis"},
    # Comentarios tipificados (US3)
    {"trigger": "confirmacion_atencion", "source": "contacto", "dest": "en_analisis"},
    {"trigger": "termina_analisis", "source": "en_analisis", "dest": "en_ejecucion"},
    {"trigger": "solicitud_informacion", "source": ["pre_analisis", "en_analisis", "en_ejecucion"],
     "dest": "pendiente_usuario"},
    {"trigger": "solicitud_cierre", "source": ["en_ejecucion", "en_pruebas"], "dest": "resuelto"},
    {"trigger": "respuesta_usuario", "source": "pendiente_usuario", "dest": "en_ejecucion"},
    # EN PRUEBAS versión simple (clarificación Q1)
    {"trigger": "enter_testing", "source": "en_ejecucion", "dest": "en_pruebas"},
    {"trigger": "exit_testing", "source": "en_pruebas", "dest": "en_ejecucion"},
    # Resolución (clarificación Q2: registrada por el equipo en nombre del usuario)
    {"trigger": "reject_resolution", "source": "resuelto", "dest": "en_ejecucion"},
    {"trigger": "close", "source": "resuelto", "dest": "cerrado"},
    # Cancelación desde cualquier estado no final
    {"trigger": "cancel", "source": [s for s in STATUSES if s not in FINAL_STATUSES],
     "dest": "cancelado"},
]

# Etiquetas en español de las acciones, para mensajes de error útiles (FR-008)
TRIGGER_LABELS = {
    "assign_resolver": "Asignar resolutor",
    "assign_qm": "Pasar a Pre-Análisis (QM)",
    "confirmacion_atencion": "Confirmación de atención",
    "termina_analisis": "Termina análisis",
    "solicitud_informacion": "Solicitud de información",
    "solicitud_cierre": "Solicitud de cierre",
    "respuesta_usuario": "Respuesta de usuario",
    "enter_testing": "Pasar a pruebas",
    "exit_testing": "Volver a ejecución",
    "reject_resolution": "Rechazar resolución",
    "close": "Cerrar",
    "cancel": "Cancelar",
}


class _TicketState:
    """Contenedor mínimo de estado para la Machine (no acopla la entidad)."""

    def __init__(self, status: str) -> None:
        self.state = status


def _build_machine(model: "_TicketState") -> Machine:
    return Machine(
        model=model,
        states=list(STATUSES),
        transitions=TRANSITIONS,
        initial=model.state,
        auto_transitions=False,
    )


def valid_triggers(status: str) -> list[str]:
    """Triggers ejecutables desde un estado dado."""
    result = []
    for t in TRANSITIONS:
        sources = t["source"] if isinstance(t["source"], list) else [t["source"]]
        if status in sources:
            result.append(t["trigger"])
    return result


def can_transition(status: str, trigger: str) -> bool:
    return trigger in valid_triggers(status)


def apply(status: str, trigger: str) -> str:
    """Ejecuta el trigger y devuelve el nuevo estado. 409 si no es válido."""
    model = _TicketState(status)
    machine = _build_machine(model)
    try:
        machine.dispatch(trigger)
    except (MachineError, AttributeError):
        acciones = ", ".join(TRIGGER_LABELS.get(t, t) for t in valid_triggers(status)) or "ninguna"
        raise InvalidTransitionError(
            "invalid_transition",
            f"Transición no permitida desde el estado actual. Acciones válidas: {acciones}",
            current_status=status,
            valid_actions=valid_triggers(status),
        )
    return model.state
