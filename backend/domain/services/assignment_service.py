"""Triage Push (US2): asignación de tickets con Gold Standard Dataset (FR-018/019)."""
import uuid

from backend.domain.entities.ticket import Ticket
from backend.domain.errors import DomainError
from backend.domain.fsm import ticket_fsm


class AssignmentError(DomainError):
    default_status_code = 400


ASSIGN_MODES = {
    "resolver": ("assign_resolver", "asignado"),
    "pre_analysis": ("assign_qm", "pre_analisis"),
}


class AssignmentService:
    def validate(self, ticket: Ticket, assignee, mode: str) -> tuple[str, str]:
        """Devuelve (trigger FSM, tipo de comentario automático)."""
        if mode not in ASSIGN_MODES:
            raise AssignmentError("validation_error", "mode debe ser 'resolver' o 'pre_analysis'")
        if assignee is None:
            raise AssignmentError("not_found", "Recurso no encontrado", status_code=404)
        if not assignee.active:
            raise AssignmentError("resource_inactive", "No se puede asignar a un recurso inactivo")
        trigger, comment_type = ASSIGN_MODES[mode]
        if not ticket_fsm.can_transition(ticket.status, trigger):
            # deja que apply() genere el 409 con las acciones válidas en español
            ticket_fsm.apply(ticket.status, trigger)
        return trigger, comment_type

    def build_context(self, assignee, open_tickets_count: int, ticket: Ticket) -> dict:
        """Snapshot inmutable de la decisión (Gold Standard Dataset, FR-019)."""
        return {
            "assignee_skills": sorted(s.code for s in (assignee.skills or [])),
            "assignee_open_tickets": open_tickets_count,
            "ticket_priority": ticket.priority,
            "ticket_severity": ticket.severity,
        }
