"""Reasignación de resolutor (spec 023): cambia el `assignee_id` de un Ticket/Tarea sin invocar
el FSM — endpoint independiente de `/assign` (research.md Decisión 3). Capa 1: sin imports de
Flask/SQLAlchemy.
"""
from backend.domain.entities.ticket import Ticket
from backend.domain.errors import DomainError

TERMINAL_STATUSES = ("cerrado", "cancelado")


class ReassignmentError(DomainError):
    default_status_code = 400


class ReassignmentService:
    def validate(self, ticket: Ticket, new_assignee) -> list[str]:
        """Valida la reasignación (FR-005 a FR-010) y devuelve los códigos de Skills requeridas
        que el nuevo resolutor no tiene — advertencia no bloqueante (FR-011), la reasignación se
        permite igual. Lanza `ReassignmentError` cuando la reasignación debe rechazarse."""
        if new_assignee is None:
            raise ReassignmentError("not_found", "Recurso no encontrado", status_code=404)
        if not new_assignee.active:
            raise ReassignmentError("resource_inactive", "No se puede reasignar a un recurso inactivo")
        if ticket.status in TERMINAL_STATUSES:
            raise ReassignmentError(
                "ticket_closed",
                f"El ticket está en estado '{ticket.status}' y no admite reasignación",
                status_code=409)
        if ticket.assignee_id and ticket.assignee_id == new_assignee.id:
            raise ReassignmentError("validation_error", "El ticket ya está asignado a ese resolutor")

        required = {s.code for s in (ticket.skills or [])}
        have = {s.code for s in (new_assignee.skills or [])}
        return sorted(required - have)
