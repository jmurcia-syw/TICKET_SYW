"""Reglas de negocio de creación/edición de tickets (US1)."""
from typing import Optional
import uuid

from backend.domain.entities.ticket import (
    Ticket, STATUSES, TICKET_TYPES, PRIORITIES, SEVERITIES, ESCALATION_LEVELS, locked_fields_for,
)
from backend.domain.entities.comment import Comment
from backend.domain.entities.user import USUARIO_CLIENTE_ROLE_NAME
from backend.domain.errors import DomainError
from backend.domain.services.rich_content_service import strip_html


class TicketBusinessError(DomainError):
    default_status_code = 409


class TicketValidationError(DomainError):
    default_status_code = 400


# Campos editables por PATCH (subconjunto; el resto nunca se edita por esa vía)
PATCHABLE_FIELDS = {
    "title", "description", "ticket_type", "priority", "severity",
    "escalation_level", "estimated_resolution_minutes", "tool_id", "process_id",
    "related_ticket_id", "client_contact_id", "list_id",
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
                        tools_repo, processes_repo, tickets_repo,
                        client_contact_id: Optional[uuid.UUID] = None,
                        client_contacts_repo=None,
                        list_id: Optional[uuid.UUID] = None, task_lists_repo=None,
                        parent_task_id: Optional[uuid.UUID] = None,
                        project_members_repo=None,
                        creator_is_client_user: bool = False,
                        creator_user_id: Optional[uuid.UUID] = None) -> None:
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
        if related_ticket_id:
            related = tickets_repo.get_by_id(related_ticket_id)
            if not related:
                raise TicketValidationError("not_found", "El ticket relacionado no existe", status_code=404)
            if related.client_id != client_id:
                raise TicketBusinessError(
                    "related_ticket_mismatch",
                    "El Registro relacionado no pertenece al cliente indicado")
        if client_contact_id:
            contact = client_contacts_repo.get_by_id(client_contact_id)
            if not contact:
                raise TicketValidationError("not_found", "El Usuario/cliente indicado no existe", status_code=404)
            if contact.client_id != client_id:
                raise TicketBusinessError(
                    "client_contact_mismatch", "El Usuario/cliente indicado no pertenece al cliente del ticket")
            # Spec 010 (US2): con proyecto, el solicitante debe ser personal del proyecto
            if project_id and project_members_repo is not None \
                    and not project_members_repo.is_member(project_id, contact.user_id):
                raise TicketBusinessError(
                    "contact_not_in_project",
                    "El Usuario/cliente indicado no está asignado al proyecto del ticket")
        # Spec 010 (FR-007): el autoservicio del Usuario/cliente queda acotado a sus proyectos
        if creator_is_client_user and project_id and project_members_repo is not None \
                and creator_user_id is not None \
                and not project_members_repo.is_member(project_id, creator_user_id):
            raise TicketBusinessError(
                "project_not_assigned", "No estás asignado a este proyecto")
        if list_id:
            task_list = task_lists_repo.get_by_id(list_id)
            if not task_list:
                raise TicketValidationError("not_found", "La Lista indicada no existe", status_code=404)
            if project_id is None or task_list.project_id != project_id:
                raise TicketBusinessError(
                    "list_mismatch", "La Lista indicada no pertenece al proyecto del registro")
        if parent_task_id:
            parent = tickets_repo.get_by_id(parent_task_id)
            if not parent:
                raise TicketValidationError("not_found", "La Tarea padre indicada no existe", status_code=404)
            if parent.parent_task_id is not None:
                raise TicketBusinessError(
                    "nested_subtask_not_allowed",
                    "No se puede crear una Subtarea dentro de otra Subtarea")
            if parent.client_id != client_id:
                raise TicketBusinessError(
                    "parent_task_mismatch", "La Tarea padre no pertenece al cliente indicado")

    def resolve_record_type(self, record_type_id: Optional[uuid.UUID], record_types_repo) -> uuid.UUID:
        """Resuelve el catálogo dinámico de tipo de registro (FR-029). Desde la Fase 3, tanto
        "Ticket" como "Tarea" son valores creables — el bloqueo que reservaba "Tarea" para esta
        fase (FR-030) se retira aquí. Un Usuario/cliente nunca llega a este método con "Tarea" porque
        su branch de autoservicio no lee `record_type_id` (ver `api/routes/tickets.py`)."""
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
        return uuid.UUID(item["id"])

    def is_task_record_type(self, record_type_id: uuid.UUID, record_types_repo) -> bool:
        """True si el `record_type_id` resuelto corresponde a "Tarea" (Fase 3)."""
        item = record_types_repo.get_by_id(record_type_id)
        return bool(item and item["name"] == "Tarea")

    def validate_patch(self, ticket: Ticket, data: dict,
                       client_contacts_repo=None, users_repo=None, tickets_repo=None,
                       task_lists_repo=None, project_members_repo=None) -> dict:
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
            try:
                related_id = uuid.UUID(str(data["related_ticket_id"]))
            except (ValueError, AttributeError):
                raise TicketValidationError("validation_error", "related_ticket_id inválido")
            related = tickets_repo.get_by_id(related_id)
            if not related:
                raise TicketValidationError(
                    "not_found", "El ticket relacionado no existe", status_code=404)
            if related.client_id != ticket.client_id:
                raise TicketBusinessError(
                    "related_ticket_mismatch",
                    "El Registro relacionado no pertenece al cliente indicado")
            data["related_ticket_id"] = related_id
        if "list_id" in data and data["list_id"] is not None:
            try:
                list_id = uuid.UUID(str(data["list_id"]))
            except (ValueError, AttributeError):
                raise TicketValidationError("validation_error", "list_id inválido")
            task_list = task_lists_repo.get_by_id(list_id)
            if not task_list:
                raise TicketValidationError("not_found", "La Lista indicada no existe", status_code=404)
            if task_list.project_id != ticket.project_id:
                raise TicketBusinessError(
                    "list_mismatch", "La Lista indicada no pertenece al proyecto del registro")
            data["list_id"] = list_id
        if "client_contact_id" in data:
            if users_repo is not None:
                creator = users_repo.get_by_id(ticket.created_by)
                if creator and creator.role.name == USUARIO_CLIENTE_ROLE_NAME:
                    raise TicketBusinessError(
                        "requester_immutable",
                        "El Usuario/cliente solicitante no se puede editar: el ticket fue creado por "
                        "un usuario con rol Usuario/cliente")
            if data["client_contact_id"] is not None:
                try:
                    contact_id = uuid.UUID(str(data["client_contact_id"]))
                except (ValueError, AttributeError):
                    raise TicketValidationError("validation_error", "client_contact_id inválido")
                contact = client_contacts_repo.get_by_id(contact_id)
                if not contact:
                    raise TicketValidationError(
                        "not_found", "El Usuario/cliente indicado no existe", status_code=404)
                if contact.client_id != ticket.client_id:
                    raise TicketBusinessError(
                        "client_contact_mismatch",
                        "El Usuario/cliente indicado no pertenece al cliente del ticket")
                # Spec 010 (US2): con proyecto, el solicitante debe ser personal del proyecto
                if ticket.project_id and project_members_repo is not None \
                        and not project_members_repo.is_member(ticket.project_id, contact.user_id):
                    raise TicketBusinessError(
                        "contact_not_in_project",
                        "El Usuario/cliente indicado no está asignado al proyecto del ticket")
                data["client_contact_id"] = contact_id
        return data

    def free_transition_task(self, ticket: Ticket, new_status: str, comment_body: str,
                             actor_id: uuid.UUID, tickets_repo, comments_repo) -> Ticket:
        """Cambia el estado de una Tarea/Subtarea a cualquier valor del catálogo compartido con
        Ticket, sin restricción de secuencia — exige un comentario que documente el cambio
        (spec 009, FR-003/FR-004/FR-005). Reemplaza `task_fsm.py` (spec 008)."""
        if new_status not in STATUSES:
            raise TicketValidationError(
                "validation_error",
                f"Estado inválido. Permitidos: {', '.join(STATUSES)}")
        if not comment_body or not strip_html(comment_body).strip():
            raise TicketValidationError(
                "validation_error",
                "Debe indicar un comentario que documente el cambio de estado")
        comment = Comment.create(ticket_id=ticket.id, comment_type="comentario_interno",
                                 body=comment_body.strip(), author_id=actor_id)
        comments_repo.add(comment, commit=False)
        previous_status = ticket.status
        tickets_repo.update_fields(ticket.id, status=new_status)
        tickets_repo.add_transition(ticket.id, previous_status, new_status, actor_id,
                                    comment_id=comment.id, commit=True)
        return tickets_repo.get_by_id(ticket.id)
