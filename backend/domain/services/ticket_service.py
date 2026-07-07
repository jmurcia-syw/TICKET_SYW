"""Reglas de negocio de creación/edición de tickets (US1)."""
from typing import Optional
import uuid

from backend.domain.entities.ticket import (
    Ticket, TICKET_TYPES, PRIORITIES, SEVERITIES, ESCALATION_LEVELS, locked_fields_for,
)
from backend.domain.errors import DomainError


class TicketBusinessError(DomainError):
    default_status_code = 409


class TicketValidationError(DomainError):
    default_status_code = 400


# Campos editables por PATCH (subconjunto; el resto nunca se edita por esa vía)
PATCHABLE_FIELDS = {
    "title", "description", "ticket_type", "priority", "severity",
    "escalation_level", "estimated_resolution_minutes", "tool_id", "process_id",
    "related_ticket_id",
}

_ENUMS = {
    "ticket_type": TICKET_TYPES,
    "priority": PRIORITIES,
    "severity": SEVERITIES,
    "escalation_level": ESCALATION_LEVELS,
}


class TicketService:
    def validate_enums(self, data: dict) -> None:
        for field_name, allowed in _ENUMS.items():
            if field_name in data and data[field_name] is not None and data[field_name] not in allowed:
                raise TicketValidationError(
                    "validation_error",
                    f"Valor inválido para '{field_name}'. Permitidos: {', '.join(allowed)}",
                )

    def validate_create(self, client_id: uuid.UUID, project_id: Optional[uuid.UUID],
                        tool_id: Optional[uuid.UUID], process_id: Optional[uuid.UUID],
                        related_ticket_id: Optional[uuid.UUID], clients_repo, projects_repo,
                        tools_repo, processes_repo, tickets_repo) -> None:
        client = clients_repo.get_by_id(client_id)
        if not client:
            raise TicketValidationError("not_found", "Cliente no encontrado", status_code=404)
        if not client.active:
            raise TicketBusinessError("client_inactive", "El cliente está inactivo")
        if project_id:
            project = projects_repo.get_by_id(project_id)
            if not project:
                raise TicketValidationError("not_found", "Proyecto no encontrado", status_code=404)
            if project.client_id != client_id:
                raise TicketValidationError("validation_error", "El proyecto no pertenece al cliente indicado")
            if not project.active:
                raise TicketBusinessError("project_inactive", "El proyecto está inactivo")
        for catalog_id, repo, label in ((tool_id, tools_repo, "herramienta"),
                                        (process_id, processes_repo, "proceso")):
            if catalog_id:
                item = repo.get_by_id(catalog_id)
                if not item:
                    raise TicketValidationError("not_found", f"Valor de {label} no encontrado", status_code=404)
                if not item["active"]:
                    raise TicketBusinessError("catalog_inactive", f"El valor de {label} está inactivo")
        if related_ticket_id and not tickets_repo.get_by_id(related_ticket_id):
            raise TicketValidationError("not_found", "El ticket relacionado no existe", status_code=404)

    def resolve_record_type(self, record_type_id: Optional[uuid.UUID], record_types_repo) -> uuid.UUID:
        """Resuelve el catálogo dinámico de tipo de registro (FR-029) y aplica el bloqueo
        de dominio: solo el valor "Ticket" puede usarse para crear en esta fase, "Tarea"
        queda reservado para Fase 3 (FR-030) aunque el catálogo ya lo tenga sembrado."""
        if record_type_id is None:
            item = record_types_repo.get_by_name("Ticket")
            if not item:
                raise TicketBusinessError(
                    "record_type_not_found",
                    "El catálogo de tipo de registro no tiene sembrado el valor 'Ticket'")
            return uuid.UUID(item["id"])
        item = record_types_repo.get_by_id(record_type_id)
        if not item:
            raise TicketValidationError(
                "not_found", "Valor de tipo de registro no encontrado", status_code=404)
        if not item["active"]:
            raise TicketBusinessError("catalog_inactive", "El valor de tipo de registro está inactivo")
        if item["name"] != "Ticket":
            raise TicketBusinessError(
                "record_type_not_allowed",
                "En esta fase solo se pueden crear tickets con tipo de registro 'Ticket' "
                "('Tarea' queda reservado para Fase 3)")
        return uuid.UUID(item["id"])

    def validate_patch(self, ticket: Ticket, data: dict) -> dict:
        """Filtra los campos del PATCH: rechaza status, campos desconocidos y bloqueados."""
        if "status" in data:
            raise TicketValidationError(
                "validation_error",
                "El estado no se edita directamente; use las acciones del ciclo de vida")
        unknown = set(data) - PATCHABLE_FIELDS
        if unknown:
            raise TicketValidationError(
                "validation_error", f"Campos no editables: {', '.join(sorted(unknown))}")
        locked = set(locked_fields_for(ticket.status)) & set(data)
        if locked:
            raise TicketBusinessError(
                "field_locked",
                f"Campo(s) bloqueado(s) en el estado actual: {', '.join(sorted(locked))}",
                locked_fields=sorted(locked))
        self.validate_enums(data)
        if "estimated_resolution_minutes" in data and data["estimated_resolution_minutes"] is not None:
            try:
                value = int(data["estimated_resolution_minutes"])
            except (TypeError, ValueError):
                raise TicketValidationError(
                    "validation_error", "estimated_resolution_minutes debe ser un entero")
            if value < 0:
                raise TicketValidationError(
                    "validation_error", "estimated_resolution_minutes no puede ser negativo")
            data["estimated_resolution_minutes"] = value
        if "related_ticket_id" in data and data["related_ticket_id"] is not None:
            if str(data["related_ticket_id"]) == str(ticket.id):
                raise TicketValidationError(
                    "validation_error", "Un ticket no puede relacionarse consigo mismo")
        return data
