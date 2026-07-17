"""Rutas de tickets: CRUD, Triage Push, ciclo de vida por comentarios, cierre y cancelación.

Todas exigen JWT + permiso del módulo `tickets` (FR-022). Las operaciones que cambian
estado son atómicas: comentario + transición + notificación en la misma transacción
(Decisión 2 de research.md).
"""
from datetime import datetime, timedelta, timezone
import logging
import uuid

from flask import g, request, send_file
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission, require_authenticated, current_user_has
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.comment import Comment, Attachment, COMMENT_TYPE_LABELS
from backend.domain.entities.ticket import Ticket, STATUSES, STATUS_LABELS
from backend.domain.entities.user import USUARIO_CLIENTE_ROLE_NAME
from backend.domain.errors import DomainError
from backend.domain.fsm import ticket_fsm
from backend.domain.services import sla_service
from backend.domain.services.assignment_service import AssignmentService
from backend.domain.services.comment_service import CommentService
from backend.domain.services.notification_service import NotificationService
from backend.domain.services.rich_content_service import resolve_pending_images, sanitize_html, strip_html
from backend.domain.services.ticket_service import TicketService, TicketValidationError
from backend.infra.database import get_db
from backend.infra.repositories.calendar_repo import (
    AbsenceRequestRepository, HolidayRepository, resolve_effective_schedule_slots,
)
from backend.infra.repositories.catalog_repo import CatalogRepository
from backend.infra.repositories.client_contact_repo import ClientContactRepository
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.comment_repo import CommentRepository
from backend.infra.repositories.notification_repo import NotificationRepository
from backend.infra.repositories.project_member_repo import ProjectMemberRepository
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.sla_rule_repo import SlaRuleRepository
from backend.infra.repositories.task_list_repo import TaskListRepository
from backend.infra.repositories.ticket_repo import TicketRepository
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.work_session_repo import WorkSessionRepository
from backend.infra.storage import attachments as attachment_storage

logger = logging.getLogger(__name__)

ns = Namespace("tickets", description="Gestión de tickets y su ciclo de vida", path="/api/tickets")

_svc = TicketService()
_assign_svc = AssignmentService()
_comment_svc = CommentService()
_notif_svc = NotificationService()

CLOSE_ELIGIBLE_DAYS = 3

# ── Swagger models ────────────────────────────────────────────────────────────

_error = error_model(ns, "TicketError")

_ticket_input = ns.model("TicketInput", {
    "title": fields.String(required=True),
    "description": fields.String(required=True),
    "ticket_type": fields.String(description="incident | evolutive | preventive — requerido "
                                              "salvo que record_type_id resuelva a 'Tarea', "
                                              "donde es opcional (se defaultea si se omite)"),
    "priority": fields.String(description="critical | high | medium | low — mismo criterio "
                                          "que ticket_type"),
    "severity": fields.String(description="s1 | s2 | s3 | s4 — mismo criterio que ticket_type"),
    "client_id": fields.String(required=True),
    "project_id": fields.String(description="Opcional: proyecto activo del cliente"),
    "client_contact_id": fields.String(description="Opcional: Usuario/cliente solicitante — debe "
                                                     "pertenecer al cliente indicado (Fase 2.2)"),
    "tool_id": fields.String(description="Catálogo herramienta"),
    "process_id": fields.String(description="Catálogo proceso"),
    "record_type_id": fields.String(description="Catálogo tipo de registro (default: valor "
                                                  "'Ticket'; 'Tarea' habilitado desde Fase 3)"),
    "escalation_level": fields.String(description="n1..n4 (default n2)"),
    "related_ticket_id": fields.String(description="Registro relacionado (Ticket o Tarea) — "
                                                     "debe pertenecer al mismo client_id"),
    "list_id": fields.String(description="Lista de tareas del mismo Proyecto (spec 009, solo "
                                          "tiene efecto en una Tarea)"),
    "parent_task_id": fields.String(description="Marca el registro como Subtarea de la Tarea "
                                                 "indicada (spec 009, Nivel 5)"),
    "assignee_id": fields.String(description="Encargado de la Tarea/Subtarea (opcional; "
                                              "default: el propio creador, spec 008 Decisión 7)"),
})

_assign_input = ns.model("TicketAssignInput", {
    "assignee_id": fields.String(required=True, description="UUID del recurso"),
    "mode": fields.String(required=True, description="resolver | pre_analysis"),
})

_comment_input = ns.model("TicketCommentInput", {
    "comment_type": fields.String(required=True),
    "body": fields.String(required=True),
})

_close_input = ns.model("TicketCloseInput", {
    "resolution_type_id": fields.String(required=True),
    "body": fields.String(required=True, description="Descripción de la solución"),
})

_testing_input = ns.model("TicketTestingInput", {
    "direction": fields.String(required=True, description="enter | exit"),
})

_resolution_input = ns.model("TicketResolutionInput", {
    "accepted": fields.Boolean(required=True, description="true = el usuario acepta la resolución"),
    "body": fields.String(description="Comentario/evidencia registrado en nombre del usuario"),
})

_cancel_input = ns.model("TicketCancelInput", {
    "body": fields.String(required=True, description="Motivo de la cancelación"),
})

_status_change_input = ns.model("StatusChangeInput", {
    "status": fields.String(required=True, description="Uno de los 10 valores del catálogo "
                                                        "compartido con Ticket"),
    "comment": fields.String(required=True, description="Comentario obligatorio que documenta "
                                                         "el cambio de estado"),
})

_entity_ref = ns.model("EntityRef", {
    "id": fields.String(description="UUID"),
    "name": fields.String(description="Nombre"),
})

_resource_ref = ns.model("ResourceRef", {
    "id": fields.String(description="UUID del recurso"),
    "full_name": fields.String(description="Nombre completo"),
})

_sla_summary_out = ns.model("TicketSlaSummary", {
    "phase": fields.String(allow_null=True, description="contacto | ejecucion | cerrado | null"),
    "status": fields.String(description="sin_sla | corriendo | pausado | vencido | detenido"),
})

_ticket_out = ns.model("Ticket", {
    "id": fields.String(description="UUID del ticket"),
    "ticket_number": fields.String(description="Consecutivo legible", example="TK-000123"),
    "record_type_id": fields.String(description="UUID del catálogo tipo de registro (Ticket/Tarea)"),
    "ticket_type": fields.String(description="incident | evolutive | preventive"),
    "title": fields.String(),
    "status": fields.String(description="Estado FSM actual"),
    "status_label": fields.String(description="Etiqueta en español"),
    "priority": fields.String(description="critical | high | medium | low"),
    "severity": fields.String(description="s1 | s2 | s3 | s4"),
    "escalation_level": fields.String(description="n1 | n2 | n3 | n4"),
    "client": fields.Nested(_entity_ref, allow_null=True),
    "project": fields.Nested(_entity_ref, allow_null=True),
    "assignee": fields.Nested(_resource_ref, allow_null=True),
    "estimated_resolution_minutes": fields.Integer(allow_null=True),
    "list_name": fields.String(allow_null=True, description="Nombre de la Lista resuelto "
                                                              "(spec 009, solo Tarea)"),
    "list_id": fields.String(allow_null=True, description="UUID de la Lista (spec 009)"),
    "record_type": fields.String(description="Ticket | Tarea (nombre resuelto)"),
    "parent_task_id": fields.String(allow_null=True, description="Si no es null, este "
                                                                  "registro es una Subtarea"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
    "sla": fields.Nested(_sla_summary_out, description="Resumen de SLA (Fase 4, spec 014) "
                                                        "para pintar el indicador sin abrir "
                                                        "el detalle (FR-008)"),
})

_ticket_list_out = ns.model("TicketList", {
    "items": fields.List(fields.Nested(_ticket_out)),
    "total": fields.Integer(description="Total de registros"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_attachment_out = ns.model("CommentAttachment", {
    "id": fields.String(description="UUID del adjunto"),
    "filename": fields.String(),
    "content_type": fields.String(),
    "size_bytes": fields.Integer(),
})

_comment_out = ns.model("TicketComment", {
    "id": fields.String(description="UUID del comentario"),
    "comment_type": fields.String(description="Tipo estructurado (catálogo FR-013)"),
    "comment_type_label": fields.String(description="Etiqueta en español"),
    "visibility": fields.String(description="internal | external"),
    "body": fields.String(),
    "author_id": fields.String(description="UUID del autor"),
    "is_automatic": fields.Boolean(description="true si lo generó una asignación (Triage Push)"),
    "attachments": fields.List(fields.Nested(_attachment_out)),
    "created_at": fields.String(description="Fecha ISO-8601"),
})

_transition_out = ns.model("TicketStatusTransition", {
    "id": fields.String(),
    "from_status": fields.String(),
    "to_status": fields.String(),
    "actor_id": fields.String(description="UUID de quien ejecutó la acción"),
    "comment_id": fields.String(allow_null=True, description="Comentario que disparó la transición"),
    "created_at": fields.String(),
})

_assignment_context_out = ns.model("AssignmentContext", {
    "assignee_skills": fields.List(fields.String(), description="Códigos de skill del asignado en el momento"),
    "assignee_open_tickets": fields.Integer(description="Tickets abiertos que tenía el asignado"),
    "ticket_priority": fields.String(),
    "ticket_severity": fields.String(),
})

_assignment_out = ns.model("TicketAssignment", {
    "id": fields.String(),
    "assigner_id": fields.String(description="UUID de quien asignó"),
    "assignee_id": fields.String(description="UUID del recurso asignado"),
    "resulting_status": fields.String(),
    "context": fields.Nested(_assignment_context_out, description="Gold Standard Dataset (FR-019)"),
    "created_at": fields.String(),
})

_requester_out = ns.model("TicketRequester", {
    "id": fields.String(description="UUID del solicitante (Usuario/cliente manual o creador automático)"),
    "name": fields.String(description="Nombre para mostrar"),
    "is_encargado": fields.Boolean(description="true si el solicitante tiene rol Usuario/cliente"),
})

_related_from_out = ns.model("RelatedFromItem", {
    "id": fields.String(description="UUID"),
    "ticket_number": fields.String(),
    "title": fields.String(),
    "record_type": fields.String(description="Ticket | Tarea"),
})

_ticket_skill_ref = ns.model("TicketSkillRef", {
    "id": fields.String(description="UUID del skill"),
    "code": fields.String(description="Código del skill"),
    "label": fields.String(description="Etiqueta del skill"),
})

_ticket_skills_update = ns.model("TicketSkillsUpdate", {
    "skill_ids": fields.List(
        fields.String, required=True,
        description="Lista completa de UUIDs de Skills requeridas (reemplaza el set actual, "
                     "spec 011 FR-001/FR-003). Array vacío deja el ticket sin Skills requeridas.",
        example=[]),
})

_sla_out = ns.model("TicketSla", {
    "phase": fields.String(allow_null=True, description="contacto | ejecucion | cerrado | null"),
    "status": fields.String(description="sin_sla | corriendo | pausado | vencido | detenido"),
    "phase_limit_minutes": fields.Integer(allow_null=True),
    "consumed_seconds": fields.Integer(),
    "rule_id": fields.String(allow_null=True),
    "contact_result": fields.String(allow_null=True, description="pendiente | cumplido | vencido | null"),
    "contact_consumed_seconds": fields.Integer(allow_null=True),
})

_ticket_detail_out = ns.inherit("TicketDetail", _ticket_out, {
    "description": fields.String(),
    "description_attachments": fields.List(
        fields.Nested(_attachment_out),
        description="Adjuntos de la descripción (spec 017) — independientes de los adjuntos "
                    "de cada comentario"),
    "tool_id": fields.String(allow_null=True),
    "process_id": fields.String(allow_null=True),
    "resolution_type_id": fields.String(allow_null=True),
    "related_ticket_id": fields.String(allow_null=True),
    "related_from": fields.List(fields.Nested(_related_from_out),
                                description="Registros que referencian a este como Registro "
                                            "relacionado (Fase 3, FR-006)"),
    "subtasks": fields.List(fields.Nested(_ticket_out),
                            description="Subtareas (Nivel 5) — solo poblado en una Tarea "
                                        "(Nivel 4); vacío para Ticket y para Subtarea (spec 009)"),
    "created_by": fields.String(description="UUID de quien creó el ticket"),
    "client_contact_id": fields.String(allow_null=True,
                                       description="Usuario/cliente solicitante asignado manualmente "
                                                    "(Fase 2.2); null si no hay o si se resuelve "
                                                    "automáticamente del creador (Fase 2.1)"),
    "requester": fields.Nested(_requester_out, allow_null=True,
                               description="Solicitante resuelto (FR-009): prioriza "
                                            "client_contact_id, si no cae al creador (Fase 2.1)"),
    "resolved_at": fields.String(allow_null=True),
    "resolution_accepted_at": fields.String(allow_null=True),
    "closed_at": fields.String(allow_null=True),
    "locked_fields": fields.List(fields.String(), description="Campos no editables en el estado actual (FR-010)"),
    "close_eligible": fields.Boolean(description="true si acepta cierre (aceptado o 3+ días resuelto)"),
    "valid_actions": fields.List(fields.String(), description="Ticket: triggers FSM ejecutables "
                                                               "desde el estado actual. Tarea/"
                                                               "Subtarea: los demás 9 estados "
                                                               "del catálogo (transición libre, "
                                                               "spec 009)."),
    "comments": fields.List(fields.Nested(_comment_out)),
    "transitions": fields.List(fields.Nested(_transition_out)),
    "assignments": fields.List(fields.Nested(_assignment_out)),
    "skills": fields.List(fields.Nested(_ticket_skill_ref),
                          description="Skills requeridas para resolverlo, opcional (spec 011)"),
    "sla": fields.Nested(_sla_out, description="Estado de SLA (Fase 4, spec 014) — solo "
                                               "calculado para record_type 'Ticket' (FR-012); "
                                               "'sin_sla' para Tareas/Subtareas"),
})

_assignment_result_ref = ns.model("AssignmentResult", {
    "id": fields.String(),
    "context": fields.Nested(_assignment_context_out),
})

_assign_result_out = ns.model("TicketAssignResult", {
    "ticket": fields.Nested(_ticket_detail_out),
    "assignment": fields.Nested(_assignment_result_ref),
})

_ticket_after_comment_ref = ns.model("TicketAfterComment", {
    "status": fields.String(),
    "status_label": fields.String(),
    "locked_fields": fields.List(fields.String()),
    "valid_actions": fields.List(fields.String()),
})

_comment_result_out = ns.model("TicketCommentResult", {
    "comment": fields.Nested(_comment_out),
    "ticket": fields.Nested(_ticket_after_comment_ref),
})

_status_result_out = ns.model("TicketStatusResult", {
    "status": fields.String(),
    "status_label": fields.String(),
    "locked_fields": fields.List(fields.String()),
})


# ── Serialización ─────────────────────────────────────────────────────────────

def _comment_to_dict(comment: Comment) -> dict:
    return {
        "id": str(comment.id),
        "comment_type": comment.comment_type,
        "comment_type_label": COMMENT_TYPE_LABELS.get(comment.comment_type, comment.comment_type),
        "visibility": comment.visibility,
        "body": comment.body,
        "author_id": str(comment.author_id),
        "is_automatic": comment.is_automatic,
        "attachments": [{
            "id": str(a.id), "filename": a.filename, "content_type": a.content_type,
            "size_bytes": a.size_bytes,
        } for a in comment.attachments],
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def _close_eligible(ticket: Ticket) -> bool:
    if ticket.status != "resuelto" or ticket.resolved_at is None:
        return False
    if ticket.resolution_accepted_at is not None:
        return True
    resolved = ticket.resolved_at
    now = datetime.now(timezone.utc) if resolved.tzinfo else datetime.utcnow()
    return (now - resolved) >= timedelta(days=CLOSE_ELIGIBLE_DAYS)


def _resolve_sla_context(db, ticket: Ticket) -> dict:
    """Resuelve `resource`/`holidays`/`schedule_slots`/`absences` para el motor de SLA dinámico
    (spec 022, research.md Decisión 10 — cierra el hallazgo C1 de `/speckit-analyze`). Sin
    recurso asignado, devuelve un contexto vacío y `sla_service.compute_state` conserva el
    wall-clock puro (parámetros opcionales, sin romper tickets sin asignar)."""
    if not ticket.assignee_id:
        return {}
    resource = ResourceRepository(db).get_by_id(ticket.assignee_id)
    if not resource:
        return {}
    holidays = HolidayRepository(db).list_by_country(resource.calendar_country) if resource.calendar_country else []
    schedule_slots = resolve_effective_schedule_slots(db, resource)
    now = datetime.now(timezone.utc)
    from_date = (ticket.sla_last_resume_at or now).date()
    absences = AbsenceRequestRepository(db).list_approved_between(resource.id, from_date, now.date())
    return {"resource": resource, "holidays": holidays, "schedule_slots": schedule_slots, "absences": absences}


def _ticket_summary(ticket: Ticket, db) -> dict:
    client = ClientRepository(db).get_by_id(ticket.client_id)
    project = ProjectRepository(db).get_by_id(ticket.project_id) if ticket.project_id else None
    assignee = ResourceRepository(db).get_by_id(ticket.assignee_id) if ticket.assignee_id else None
    task_list = TaskListRepository(db).get_by_id(ticket.list_id) if ticket.list_id else None
    sla_state = sla_service.compute_state(ticket, datetime.now(timezone.utc), **_resolve_sla_context(db, ticket))
    return {
        "id": str(ticket.id),
        "ticket_number": ticket.number_display,
        "record_type_id": str(ticket.record_type_id) if ticket.record_type_id else None,
        "ticket_type": ticket.ticket_type,
        "title": ticket.title,
        "status": ticket.status,
        "status_label": STATUS_LABELS[ticket.status],
        "priority": ticket.priority,
        "severity": ticket.severity,
        "escalation_level": ticket.escalation_level,
        "client": {"id": str(client.id), "name": client.name} if client else None,
        "project": {"id": str(project.id), "name": project.name} if project else None,
        "assignee": {"id": str(assignee.id), "full_name": assignee.full_name} if assignee else None,
        "estimated_resolution_minutes": ticket.estimated_resolution_minutes,
        "list_name": task_list.name if task_list else None,
        "list_id": str(ticket.list_id) if ticket.list_id else None,
        "record_type": _record_type_name(ticket.record_type_id, db),
        "parent_task_id": str(ticket.parent_task_id) if ticket.parent_task_id else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "sla": {"phase": sla_state["phase"], "status": sla_state["status"],
                "pause_reason": sla_state["pause_reason"]},
    }


def _requester(ticket: Ticket, db) -> dict | None:
    """Resuelve el solicitante (Fase 2.2): prioriza `client_contact_id` (Usuario/cliente asignado
    manualmente); si no está presente, cae al comportamiento ya existente de Fase 2.1
    (`created_by` resuelto a nombre + `is_encargado`)."""
    if ticket.client_contact_id:
        contact = ClientContactRepository(db).get_by_id(ticket.client_contact_id)
        if contact:
            contact_user = UserRepository(db).get_by_id(contact.user_id)
            if contact_user:
                return {"id": str(contact_user.id), "name": contact_user.username, "is_encargado": True}
    creator = UserRepository(db).get_by_id(ticket.created_by)
    if not creator:
        return None
    return {"id": str(creator.id), "name": creator.username,
            "is_encargado": creator.role.name == USUARIO_CLIENTE_ROLE_NAME}


def _is_task(ticket: Ticket, db) -> bool:
    record_type = CatalogRepository(db, "record-types").get_by_id(ticket.record_type_id)
    return bool(record_type and record_type["name"] == "Tarea")


def _record_type_name(record_type_id, db) -> str:
    record_type = CatalogRepository(db, "record-types").get_by_id(record_type_id)
    return record_type["name"] if record_type else "Ticket"


def _related_from(ticket: Ticket, db) -> list[dict]:
    return [
        {
            "id": str(r.id), "ticket_number": r.number_display, "title": r.title,
            "record_type": _record_type_name(r.record_type_id, db),
        }
        for r in TicketRepository(db).list_related_from(ticket.id)
    ]


def _ticket_detail(ticket: Ticket, db) -> dict:
    d = _ticket_summary(ticket, db)
    is_task = _is_task(ticket, db)
    is_subtask = is_task and ticket.parent_task_id is not None
    subtasks = (TicketRepository(db).list_subtasks(ticket.id)
                if is_task and not is_subtask else [])
    d.update({
        "description": ticket.description,
        "description_attachments": [
            {"id": str(a.id), "filename": a.filename, "content_type": a.content_type,
             "size_bytes": a.size_bytes}
            for a in CommentRepository(db).list_ticket_attachments(ticket.id)
        ],
        "tool_id": str(ticket.tool_id) if ticket.tool_id else None,
        "process_id": str(ticket.process_id) if ticket.process_id else None,
        "estimated_resolution_minutes": ticket.estimated_resolution_minutes,
        "resolution_type_id": str(ticket.resolution_type_id) if ticket.resolution_type_id else None,
        "related_ticket_id": str(ticket.related_ticket_id) if ticket.related_ticket_id else None,
        "related_from": _related_from(ticket, db),
        "subtasks": [_ticket_summary(s, db) for s in subtasks],
        "created_by": str(ticket.created_by),
        "client_contact_id": str(ticket.client_contact_id) if ticket.client_contact_id else None,
        "requester": _requester(ticket, db),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "resolution_accepted_at": ticket.resolution_accepted_at.isoformat() if ticket.resolution_accepted_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "locked_fields": ticket.locked_fields(),
        "close_eligible": _close_eligible(ticket),
        "valid_actions": [s for s in STATUSES if s != ticket.status] if is_task
                          else ticket_fsm.valid_triggers(ticket.status),
        "comments": [_comment_to_dict(c) for c in CommentRepository(db).list_for_ticket(ticket.id)],
        "transitions": TicketRepository(db).list_transitions(ticket.id),
        "assignments": TicketRepository(db).list_assignments(ticket.id),
        "skills": [{"id": str(s.id), "code": s.code, "label": s.label} for s in (ticket.skills or [])],
        "sla": sla_service.compute_state(ticket, datetime.now(timezone.utc), **_resolve_sla_context(db, ticket)),
    })
    return d


# ── Helpers de autoría (FR-028) ───────────────────────────────────────────────

def _actor_context(db) -> tuple[uuid.UUID, bool, uuid.UUID | None]:
    """(user_id, puede_gestionar_cualquier_ticket, resource_id_vinculado)."""
    user = g.current_user
    can_manage = current_user_has("tickets", "assign")
    resource = ResourceRepository(db).get_by_user_id(user.id)
    return user.id, can_manage, resource.id if resource else None


def _get_ticket_or_404(db, ticket_id: str):
    uid = parse_uuid(ticket_id)
    if not uid:
        return None, ({"error": "validation_error", "message": "ID de ticket inválido"}, 400)
    ticket = TicketRepository(db).get_by_id(uid)
    if not ticket:
        return None, ({"error": "not_found", "message": "Ticket no encontrado"}, 404)
    return ticket, None


def _sla_updates_for_transition(db, ticket: Ticket, new_status: str) -> dict:
    """Efecto lateral de SLA sobre una transición de estado (Fase 4, spec 014, FR-014).

    Nunca debe romper la transición ya validada/aplicada por el llamador: cualquier excepción
    se registra en el log y se ignora, devolviendo un dict vacío (sin cambios de SLA) — el SLA
    es de solo medición, no una regla de negocio que pueda bloquear el ciclo de vida del ticket.
    Solo aplica a `record_type` == "Ticket" (FR-012); para Tareas/Subtareas siempre es un no-op.
    """
    try:
        if _is_task(ticket, db):
            return {}
        updates = sla_service.apply_transition(
            ticket, new_status, datetime.now(timezone.utc), SlaRuleRepository(db))
        return updates or {}
    except Exception:
        logger.exception("SLA sync failed for ticket %s (-> %s)", ticket.id, new_status)
        return {}


def _apply_transition(db, ticket: Ticket, trigger: str, actor_id: uuid.UUID,
                      comment_id: uuid.UUID | None = None,
                      extra_fields: dict | None = None) -> Ticket:
    """Ejecuta la transición FSM y registra el histórico (sin commit)."""
    new_status = ticket_fsm.apply(ticket.status, trigger)
    repo = TicketRepository(db)
    fields_to_set = {"status": new_status, **_sla_updates_for_transition(db, ticket, new_status),
                     **(extra_fields or {})}
    updated = repo.update_fields(ticket.id, **fields_to_set)
    repo.add_transition(ticket.id, ticket.status, new_status, actor_id,
                        comment_id=comment_id, commit=True)
    return updated


# ── Rutas ─────────────────────────────────────────────────────────────────────

@ns.route("")
class TicketList(Resource):
    @ns.doc("list_tickets", params={
        "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
        "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
        "search": {"description": "Búsqueda por título o número (TK-000123 o solo dígitos)", "type": "string"},
        "client_id": {"description": "Filtrar por UUID de cliente", "type": "string"},
        "project_id": {"description": "Filtrar por UUID de proyecto", "type": "string"},
        "status": {"description": "Filtrar por estado (repetible, ej. ?status=nuevo&status=contacto)", "type": "string"},
        "priority": {"description": "critical | high | medium | low", "type": "string"},
        "severity": {"description": "s1 | s2 | s3 | s4", "type": "string"},
        "ticket_type": {"description": "incident | evolutive | preventive", "type": "string"},
        "assignee_id": {"description": "Filtrar por UUID de recurso asignado", "type": "string"},
        "escalation_level": {"description": "n1 | n2 | n3 | n4", "type": "string"},
        "sort": {"description": "urgency | created_at | -created_at | priority | -priority | status "
                                 "(default: urgency — prioridad real, luego severidad, luego más antiguo primero; "
                                 "OBS-0028)", "type": "string"},
        "sla_status": {"description": "sin_sla | corriendo | pausado | vencido | detenido "
                                       "(Fase 4, spec 014)", "type": "string"},
        "sla_expiring_within_hours": {"description": "Tickets con SLA corriendo cuyo tiempo "
                                                       "restante cae dentro de N horas (Fase 4, "
                                                       "FR-009)", "type": "integer"},
    })
    @ns.response(200, "Listado de tickets", _ticket_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:view ni tickets:view_own", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self):
        """Listado paginado con filtros combinables. Con solo `tickets:view_own`
        (Usuario/cliente) se ignora cualquier filtro y se fuerza `created_by = usuario actual`."""
        if not (current_user_has("tickets", "view") or current_user_has("tickets", "view_own")):
            return {"error": "forbidden", "message": "Acceso denegado"}, 403
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        own_only = not current_user_has("tickets", "view")
        statuses = None if own_only else (request.args.getlist("status") or None)
        sla_expiring_within_hours = None
        if not own_only and request.args.get("sla_expiring_within_hours") is not None:
            try:
                sla_expiring_within_hours = int(request.args["sla_expiring_within_hours"])
            except ValueError:
                return {"error": "validation_error",
                        "message": "sla_expiring_within_hours debe ser un entero"}, 400
        try:
            db = get_db()
            items, total = TicketRepository(db).list_paginated(
                page=page, page_size=page_size,
                search=None if own_only else (request.args.get("search", "").strip() or None),
                client_id=None if own_only else (parse_uuid(request.args.get("client_id") or "") or None),
                project_id=None if own_only else (parse_uuid(request.args.get("project_id") or "") or None),
                statuses=statuses,
                priority=None if own_only else (request.args.get("priority") or None),
                severity=None if own_only else (request.args.get("severity") or None),
                ticket_type=None if own_only else (request.args.get("ticket_type") or None),
                assignee_id=None if own_only else (parse_uuid(request.args.get("assignee_id") or "") or None),
                escalation_level=None if own_only else (request.args.get("escalation_level") or None),
                sort=request.args.get("sort", "urgency"),
                created_by=g.current_user.id if own_only else None,
                sla_status=None if own_only else (request.args.get("sla_status") or None),
                sla_expiring_within_hours=sla_expiring_within_hours,
            )
            return {"items": [_ticket_summary(t, db) for t in items],
                    "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_ticket")
    @ns.expect(_ticket_input, validate=False)
    @ns.response(201, "Ticket creado (nace en estado NUEVO)", _ticket_detail_out)
    @ns.response(400, "Datos inválidos, enum desconocido, o adjunto/imagen no permitida "
                      "(attachment_error, spec 017)", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:create", _error)
    @ns.response(404, "Cliente, proyecto, catálogo o client_contact_id no encontrado", _error)
    @ns.response(409, "Cliente/proyecto/catálogo inactivo, record_type_id no permitido, el "
                      "Usuario/cliente no tiene cliente asociado (no_client_contact), "
                      "client_contact_id no pertenece al cliente indicado "
                      "(client_contact_mismatch), el solicitante no es personal del proyecto "
                      "(contact_not_in_project, spec 010), o el autoservicio eligió un proyecto "
                      "al que no está vinculado (project_not_assigned, spec 010)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "create")
    def post(self):
        """Crear un ticket, una Tarea o una Subtarea (FR-001/002; Fase 3; spec 009 FR-001..
        FR-016). Un Usuario/cliente solo envía `title`/`description` (y opcionalmente un
        `project_id` de sus proyectos vinculados, spec 010): el resto se completa
        automáticamente (research.md Decisión 4 de la spec 008) y nunca puede crear una Tarea.
        Un registro no-Usuario/cliente con `record_type_id` de "Tarea" no está obligado a enviar
        `ticket_type`/`priority`/`severity` (se defaultean en silencio si se omiten, spec 008
        Decisión 1 — pero, a diferencia de la spec 008, si se envían se respetan) y nace en
        estado "nuevo" como cualquier registro (spec 009 revierte el estado inicial "pendiente"
        de la spec 008 — mismo catálogo compartido con Ticket). Acepta `application/json` (sin
        adjuntos) o `multipart/form-data` con los mismos campos como partes de formulario, más
        `inline_images` (imágenes pegadas en `description` vía `data-pending-id`) y/o
        `attachments` (adjuntos manuales, mismas reglas que en comentarios) — spec 017."""
        if request.content_type and "multipart/form-data" in request.content_type:
            # spec 017: descripción con imágenes pegadas y/o adjuntos manuales al crear
            data = request.form.to_dict()
            inline_image_files = request.files.getlist("inline_images")
            attachment_files = request.files.getlist("attachments")
        else:
            data = request.get_json(silent=True)
            if not data:
                return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
            inline_image_files = []
            attachment_files = []

        def _missing(field_name: str) -> bool:
            if field_name == "description":
                return not strip_html(data.get(field_name) or "").strip()
            return not data.get(field_name)

        db = get_db()
        is_encargado = g.current_user.role.name == USUARIO_CLIENTE_ROLE_NAME
        if is_encargado:
            for field_name in ("title", "description"):
                if _missing(field_name):
                    return {"error": "validation_error", "message": f"El campo '{field_name}' es requerido"}, 400
            contact = ClientContactRepository(db).get_by_user_id(g.current_user.id)
            if not contact:
                return {"error": "no_client_contact",
                        "message": "Tu cuenta no tiene un cliente asociado; contactá al equipo de soporte"}, 409
            client_id = contact.client_id
            ticket_type, priority, severity = "incident", "medium", "s3"
            # Spec 010 (FR-007): el autoservicio puede elegir Proyecto, acotado a sus
            # membresías (validado en validate_create → 409 project_not_assigned)
            project_id = parse_uuid(data["project_id"]) if data.get("project_id") else None
            tool_id = process_id = related_id = record_type_id = client_contact_id = None
            list_id = parent_task_id = None
        else:
            for field_name in ("title", "description", "client_id"):
                if _missing(field_name):
                    return {"error": "validation_error", "message": f"El campo '{field_name}' es requerido"}, 400
            client_id = parse_uuid(data["client_id"])
            if not client_id:
                return {"error": "validation_error", "message": "client_id inválido"}, 400
            project_id = parse_uuid(data["project_id"]) if data.get("project_id") else None
            tool_id = parse_uuid(data["tool_id"]) if data.get("tool_id") else None
            process_id = parse_uuid(data["process_id"]) if data.get("process_id") else None
            record_type_id = parse_uuid(data["record_type_id"]) if data.get("record_type_id") else None
            related_id = parse_uuid(data["related_ticket_id"]) if data.get("related_ticket_id") else None
            client_contact_id = parse_uuid(data["client_contact_id"]) if data.get("client_contact_id") else None
            list_id = parse_uuid(data["list_id"]) if data.get("list_id") else None
            parent_task_id = parse_uuid(data["parent_task_id"]) if data.get("parent_task_id") else None
        try:
            resolved_record_type_id = _svc.resolve_record_type(
                record_type_id, CatalogRepository(db, "record-types"))
            is_task = (not is_encargado) and _svc.is_task_record_type(
                resolved_record_type_id, CatalogRepository(db, "record-types"))
            if parent_task_id and not is_task:
                return {"error": "validation_error",
                        "message": "Solo una Tarea puede tener parent_task_id (Subtarea)"}, 400
            task_assignee_id = None
            if is_task:
                ticket_type = data.get("ticket_type") or "incident"
                priority = data.get("priority") or "medium"
                severity = data.get("severity") or "s3"
                # Encargado de la Tarea/Subtarea (spec 009 FR-015/FR-001): explícito si viene en
                # el payload, si no se autoasigna al creador (spec 008 Decisión 7) para que
                # aparezca de inmediato en "Mis Tareas" — sin esto quedaría huérfana, ya que
                # create() nunca asigna un ticket por defecto (el Triage Push de un Ticket
                # normal es un paso manual y deliberado, FR-002 Fase 1).
                if data.get("assignee_id"):
                    explicit_assignee_id = parse_uuid(str(data["assignee_id"]))
                    if not explicit_assignee_id:
                        return {"error": "validation_error", "message": "assignee_id inválido"}, 400
                    assignee = ResourceRepository(db).get_by_id(explicit_assignee_id)
                    if not assignee:
                        return {"error": "not_found", "message": "El recurso indicado no existe"}, 404
                    task_assignee_id = assignee.id
                else:
                    creator_resource = ResourceRepository(db).get_by_user_id(g.current_user.id)
                    task_assignee_id = creator_resource.id if creator_resource else None
            elif not is_encargado:
                for field_name in ("ticket_type", "priority", "severity"):
                    if not data.get(field_name):
                        return {"error": "validation_error",
                                "message": f"El campo '{field_name}' es requerido"}, 400
                ticket_type, priority, severity = data["ticket_type"], data["priority"], data["severity"]
            _svc.validate_enums({"ticket_type": ticket_type, "priority": priority, "severity": severity})
            _svc.validate_create(
                client_id=client_id, project_id=project_id, tool_id=tool_id,
                process_id=process_id, related_ticket_id=related_id,
                clients_repo=ClientRepository(db), projects_repo=ProjectRepository(db),
                tools_repo=CatalogRepository(db, "tools"),
                processes_repo=CatalogRepository(db, "processes"),
                tickets_repo=TicketRepository(db),
                client_contact_id=client_contact_id,
                client_contacts_repo=ClientContactRepository(db),
                list_id=list_id, task_lists_repo=TaskListRepository(db),
                parent_task_id=parent_task_id,
                project_members_repo=ProjectMemberRepository(db),
                creator_is_client_user=is_encargado,
                creator_user_id=g.current_user.id,
            )
            if parent_task_id:
                parent_ticket = TicketRepository(db).get_by_id(parent_task_id)
                if parent_ticket and not _is_task(parent_ticket, db):
                    raise DomainError(
                        "parent_task_mismatch",
                        "La Tarea padre indicada es un Ticket, no una Tarea", status_code=409)
                # Una Subtarea hereda la Lista de su Tarea padre en creación — no tiene Lista
                # propia editable después (spec 009, Assumptions).
                if parent_ticket and list_id is None:
                    list_id = parent_ticket.list_id
            # SLA (Fase 4, spec 014, FR-012): solo se calcula para record_type "Ticket", nunca
            # para Tareas/Subtareas. Un fallo aquí no debe impedir la creación del ticket.
            sla_fields: dict = {}
            if not is_task:
                try:
                    sla_fields = sla_service.initial_state(
                        project_id, priority, SlaRuleRepository(db), datetime.now(timezone.utc))
                except Exception:
                    logger.exception("SLA init failed for new ticket")

            # spec 017: valida adjuntos/imágenes ANTES de escribir nada; el id del Ticket se
            # genera ya para poder resolver las URLs de las imágenes pegadas en su descripción
            ticket_id = uuid.uuid4()
            staged_inline = []
            id_by_index: dict[int, str] = {}
            for index, f in enumerate(inline_image_files):
                content = f.read()
                attachment_storage.validate(f.filename, len(content))
                attachment_id = uuid.uuid4()
                id_by_index[index] = str(attachment_id)
                staged_inline.append((attachment_id, f.filename, f.content_type or "application/octet-stream", content))
            staged_attachments = []
            for f in attachment_files:
                content = f.read()
                attachment_storage.validate(f.filename, len(content))
                staged_attachments.append((f.filename, f.content_type or "application/octet-stream", content))
            # Reescribe los `data-pending-id` ANTES de sanear: `sanitize_html` no conoce ese
            # atributo temporal (no está en la lista blanca) y lo despojaría antes de poder
            # resolverlo a la URL real del adjunto.
            description = resolve_pending_images(
                str(data["description"]).strip(), id_by_index, f"/api/tickets/{ticket_id}/attachments")
            description = sanitize_html(description)

            ticket = Ticket(
                id=ticket_id, ticket_number=0,  # lo asigna la secuencia
                title=str(data["title"]).strip(), description=description,
                ticket_type=ticket_type, priority=priority,
                severity=severity, client_id=client_id,
                status="nuevo",
                escalation_level=data.get("escalation_level") or "n2",
                project_id=project_id, tool_id=tool_id, process_id=process_id,
                record_type_id=resolved_record_type_id,
                related_ticket_id=related_id, created_by=g.current_user.id,
                client_contact_id=client_contact_id, list_id=list_id,
                parent_task_id=parent_task_id, assignee_id=task_assignee_id,
                **sla_fields,
            )
            created = TicketRepository(db).create(ticket)
            comment_repo = CommentRepository(db)
            for attachment_id, filename, content_type, content in staged_inline:
                path = attachment_storage.save(created.id, filename, content)
                comment_repo.add_attachment(Attachment(
                    id=attachment_id, ticket_id=created.id, filename=filename,
                    content_type=content_type, size_bytes=len(content), storage_path=path,
                ))
            for filename, content_type, content in staged_attachments:
                path = attachment_storage.save(created.id, filename, content)
                comment_repo.add_attachment(Attachment(
                    id=uuid.uuid4(), ticket_id=created.id, filename=filename,
                    content_type=content_type, size_bytes=len(content), storage_path=path,
                ))
            return _ticket_detail(created, db), 201, {"Location": f"/api/tickets/{created.id}"}
        except attachment_storage.AttachmentError as e:
            return {"error": "attachment_error", "message": e.message}, 400
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>")
@ns.param("ticket_id", "UUID del ticket")
class TicketDetail(Resource):
    @ns.doc("get_ticket")
    @ns.response(200, "Detalle del ticket (campos, locked_fields, close_eligible, historiales)", _ticket_detail_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:view ni tickets:view_own", _error)
    @ns.response(404, "Ticket no encontrado (o, con solo tickets:view_own, ticket ajeno)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self, ticket_id: str):
        """Detalle completo: campos, locked_fields, close_eligible, historiales. Con solo
        `tickets:view_own` (Usuario/cliente), un ticket ajeno responde 404 (no 403 — no confirma
        su existencia)."""
        if not (current_user_has("tickets", "view") or current_user_has("tickets", "view_own")):
            return {"error": "forbidden", "message": "Acceso denegado"}, 403
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            if not current_user_has("tickets", "view") and ticket.created_by != g.current_user.id:
                return {"error": "not_found", "message": "Ticket no encontrado"}, 404
            return _ticket_detail(ticket, db), 200
        except Exception:
            return server_error()

    @ns.doc("update_ticket")
    @ns.response(200, "Ticket actualizado", _ticket_detail_out)
    @ns.response(400, "Datos inválidos, campo desconocido o intento de editar `status`", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:edit", _error)
    @ns.response(404, "Ticket, o client_contact_id, no encontrado", _error)
    @ns.response(409, "Campo bloqueado por el estado actual (`field_locked`), "
                      "client_contact_id no pertenece al cliente (`client_contact_mismatch`), "
                      "el solicitante no es personal del proyecto (`contact_not_in_project`, "
                      "spec 010), o el ticket fue creado por un Usuario/cliente "
                      "(`requester_immutable`)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "edit")
    def patch(self, ticket_id: str):
        """Editar campos NO bloqueados por el estado (FR-010). `status` nunca por esta vía."""
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            clean = _svc.validate_patch(
                ticket, dict(data),
                client_contacts_repo=ClientContactRepository(db), users_repo=UserRepository(db),
                tickets_repo=TicketRepository(db), task_lists_repo=TaskListRepository(db),
                project_members_repo=ProjectMemberRepository(db),
            )
            if "description" in clean:
                clean["description"] = sanitize_html(str(clean["description"] or ""))
            for uuid_field in ("tool_id", "process_id", "related_ticket_id"):
                if uuid_field in clean and clean[uuid_field] is not None:
                    parsed = parse_uuid(str(clean[uuid_field]))
                    if not parsed:
                        return {"error": "validation_error", "message": f"{uuid_field} inválido"}, 400
                    clean[uuid_field] = parsed
            # SLA (FR-011, clarificación 2026-07-14): `project_id` no es editable en este
            # sistema (no está en PATCHABLE_FIELDS) — en la práctica solo `priority` puede
            # disparar el recálculo de la regla aplicable a la fase vigente.
            if "priority" in clean and clean["priority"] != ticket.priority and not _is_task(ticket, db):
                try:
                    sla_updates = sla_service.recalc_rule_for_project_or_priority_change(
                        ticket, ticket.project_id, clean["priority"],
                        datetime.now(timezone.utc), SlaRuleRepository(db))
                    if sla_updates:
                        clean.update(sla_updates)
                except Exception:
                    logger.exception("SLA recalculation failed for ticket %s (priority change)", ticket.id)
            updated = TicketRepository(db).update_fields(ticket.id, **clean)
            return _ticket_detail(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/skills")
@ns.param("ticket_id", "UUID del ticket")
class TicketSkills(Resource):
    @ns.doc("update_ticket_skills")
    @ns.expect(_ticket_skills_update, validate=False)
    @ns.response(200, "Skills requeridas actualizadas (reemplaza la lista completa)", _ticket_detail_out)
    @ns.response(400, "UUID inválido o cuerpo sin skill_ids", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:edit", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "edit")
    def patch(self, ticket_id: str):
        """Reemplaza el set completo de Skills requeridas del ticket (spec 011). Funciona en
        cualquier estado del ticket, incluidos Cerrado y Cancelado (FR-002) — no pasa por
        `locked_fields_for`, no dispara notificación ni exige comentario (FR-006)."""
        uid = parse_uuid(ticket_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de ticket inválido"}, 400
        data = request.get_json(silent=True) or {}
        skill_ids = [parse_uuid(sid) for sid in data.get("skill_ids", [])]
        skill_ids = [s for s in skill_ids if s]
        try:
            db = get_db()
            updated = TicketRepository(db).update_skills(uid, skill_ids)
            if not updated:
                return {"error": "not_found", "message": "Ticket no encontrado"}, 404
            return _ticket_detail(updated, db), 200
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/assign")
@ns.param("ticket_id", "UUID del ticket")
class TicketAssign(Resource):
    @ns.doc("assign_ticket")
    @ns.expect(_assign_input, validate=False)
    @ns.response(200, "Asignación registrada (comentario + transición + notificación atómicos)", _assign_result_out)
    @ns.response(400, "assignee_id faltante, mode inválido o recurso inactivo", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:assign", _error)
    @ns.response(404, "Ticket o recurso no encontrado", _error)
    @ns.response(409, "Transición no permitida desde el estado actual", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "assign")
    def post(self, ticket_id: str):
        """Triage Push (FR-018/019): asignación atómica con Gold Standard Dataset.

        Endpoint independiente de la UI — hoy lo invoca el humano, mañana el Triage Agent.
        """
        data = request.get_json(silent=True) or {}
        assignee_id = parse_uuid(str(data.get("assignee_id", "")))
        mode = data.get("mode", "resolver")
        if not assignee_id:
            return {"error": "validation_error", "message": "assignee_id es requerido"}, 400
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            resource_repo = ResourceRepository(db)
            assignee = resource_repo.get_by_id(assignee_id)
            trigger, comment_type = _assign_svc.validate(ticket, assignee, mode)

            ticket_repo = TicketRepository(db)
            open_count = ticket_repo.count_open_by_assignee(assignee_id)
            context = _assign_svc.build_context(assignee, open_count, ticket)

            # operación atómica: comentario + estado + assignment + notificación
            comment = Comment.create(
                ticket_id=ticket.id, comment_type=comment_type,
                body=f"Asignado a {assignee.full_name} por {g.current_user.username}",
                author_id=g.current_user.id, is_automatic=True,
            )
            CommentRepository(db).add(comment, commit=False)
            new_status = ticket_fsm.apply(ticket.status, trigger)
            sla_updates = _sla_updates_for_transition(db, ticket, new_status)
            ticket_repo.update_fields(ticket.id, status=new_status, assignee_id=assignee_id,
                                      **sla_updates)
            ticket_repo.add_transition(ticket.id, ticket.status, new_status,
                                       g.current_user.id, comment_id=comment.id, commit=False)
            assignment_id = ticket_repo.add_assignment(
                ticket.id, g.current_user.id, assignee_id, new_status, context, commit=False)
            if assignee.user_id:
                NotificationRepository(db).add(
                    _notif_svc.build(assignee.user_id, "assigned", ticket.id,
                                     ticket.ticket_number, ticket.title), commit=False)
            db.commit()

            updated = ticket_repo.get_by_id(ticket.id)
            return {"ticket": _ticket_detail(updated, db),
                    "assignment": {"id": str(assignment_id), "context": context}}, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/comments")
@ns.param("ticket_id", "UUID del ticket")
class TicketComments(Resource):
    @ns.doc("add_ticket_comment", description=(
        "Acepta `application/json` (sin adjuntos) o `multipart/form-data` con uno o más "
        "campos `files` (adjuntos manuales, máx 10 MB c/u, tipos permitidos) y/o "
        "`inline_images` (imágenes pegadas incrustadas en `body` vía `data-pending-id`, "
        "spec 017). Los tipos con efecto de transición (confirmacion_atencion, "
        "solicitud_informacion, termina_analisis, solicitud_cierre, respuesta_usuario) "
        "mueven el ticket en la misma operación."
    ))
    @ns.expect(_comment_input, validate=False)
    @ns.response(201, "Comentario registrado (y transición aplicada si el tipo lo dispara)", _comment_result_out)
    @ns.response(400, "Tipo inválido, comentario vacío o adjunto no permitido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso, o ticket no asignado al Resolutor (FR-028)", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "Transición no permitida desde el estado actual", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "transition")
    def post(self, ticket_id: str):
        """Comentario tipificado: ejecuta la transición de la matriz atómicamente (FR-014)."""
        if request.content_type and "multipart/form-data" in request.content_type:
            comment_type = request.form.get("comment_type", "")
            body = request.form.get("body", "")
            files = request.files.getlist("files")
            inline_images = request.files.getlist("inline_images")
        else:
            data = request.get_json(silent=True) or {}
            comment_type = data.get("comment_type", "")
            body = data.get("body", "")
            files = []
            inline_images = []
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            actor_id, can_manage, actor_resource_id = _actor_context(db)
            trigger = _comment_svc.validate(ticket, comment_type, body, actor_id,
                                            can_manage, actor_resource_id)

            # valida adjuntos ANTES de escribir nada
            staged = []
            for f in files:
                content = f.read()
                attachment_storage.validate(f.filename, len(content))
                staged.append((f.filename, f.content_type or "application/octet-stream", content))
            staged_inline = []
            id_by_index: dict[int, str] = {}
            for index, f in enumerate(inline_images):
                content = f.read()
                attachment_storage.validate(f.filename, len(content))
                attachment_id = uuid.uuid4()
                id_by_index[index] = str(attachment_id)
                staged_inline.append((attachment_id, f.filename, f.content_type or "application/octet-stream", content))
            # Reescribe los `data-pending-id` ANTES de sanear: `sanitize_html` no conoce ese
            # atributo temporal (no está en la lista blanca) y lo despojaría antes de poder
            # resolverlo a la URL real del adjunto.
            body = resolve_pending_images(
                body, id_by_index, f"/api/tickets/{ticket.id}/attachments")
            body = sanitize_html(body)

            comment = Comment.create(ticket_id=ticket.id, comment_type=comment_type,
                                     body=body.strip(), author_id=actor_id)
            comment_repo = CommentRepository(db)
            comment_repo.add(comment, commit=False)
            for filename, content_type, content in staged:
                path = attachment_storage.save(ticket.id, filename, content)
                comment_repo.add_attachment(Attachment(
                    id=uuid.uuid4(), comment_id=comment.id, filename=filename,
                    content_type=content_type, size_bytes=len(content), storage_path=path,
                ), commit=False)
            for attachment_id, filename, content_type, content in staged_inline:
                path = attachment_storage.save(ticket.id, filename, content)
                comment_repo.add_attachment(Attachment(
                    id=attachment_id, comment_id=comment.id, filename=filename,
                    content_type=content_type, size_bytes=len(content), storage_path=path,
                ), commit=False)

            updated = ticket
            if trigger is not None:
                extra: dict = {}
                if trigger == "solicitud_cierre":
                    extra["resolved_at"] = datetime.now(timezone.utc)
                    extra["resolution_accepted_at"] = None
                new_status = ticket_fsm.apply(ticket.status, trigger)
                ticket_repo = TicketRepository(db)
                sla_updates = _sla_updates_for_transition(db, ticket, new_status)
                ticket_repo.update_fields(ticket.id, status=new_status, **sla_updates, **extra)
                ticket_repo.add_transition(ticket.id, ticket.status, new_status,
                                           actor_id, comment_id=comment.id, commit=False)
                # notificación al resolutor cuando el usuario responde (FR-023)
                if trigger == "respuesta_usuario" and ticket.assignee_id:
                    assignee = ResourceRepository(db).get_by_id(ticket.assignee_id)
                    if assignee and assignee.user_id:
                        NotificationRepository(db).add(
                            _notif_svc.build(assignee.user_id, "user_replied", ticket.id,
                                             ticket.ticket_number), commit=False)
            db.commit()
            updated = TicketRepository(db).get_by_id(ticket.id)
            saved_comment = comment_repo.get_by_id(comment.id)
            return {"comment": _comment_to_dict(saved_comment),
                    "ticket": {"status": updated.status,
                               "status_label": STATUS_LABELS[updated.status],
                               "locked_fields": updated.locked_fields(),
                               "valid_actions": ticket_fsm.valid_triggers(updated.status)}}, 201
        except attachment_storage.AttachmentError as e:
            return {"error": "attachment_error", "message": e.message}, 400
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/testing")
@ns.param("ticket_id", "UUID del ticket")
class TicketTesting(Resource):
    @ns.doc("toggle_testing")
    @ns.expect(_testing_input, validate=False)
    @ns.response(200, "Ticket movido (EN EJECUCIÓN ⇄ EN PRUEBAS)", _status_result_out)
    @ns.response(400, "direction inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso, o ticket no asignado al Resolutor", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "Transición no permitida desde el estado actual", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "transition")
    def post(self, ticket_id: str):
        """EN PRUEBAS versión simple (clarificación Q1): enter | exit"""
        data = request.get_json(silent=True) or {}
        direction = data.get("direction")
        if direction not in ("enter", "exit"):
            return {"error": "validation_error", "message": "direction debe ser 'enter' o 'exit'"}, 400
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            actor_id, can_manage, actor_resource_id = _actor_context(db)
            if not can_manage and (actor_resource_id is None or ticket.assignee_id != actor_resource_id):
                return {"error": "forbidden", "message": "Solo puedes avanzar tickets asignados a ti"}, 403
            trigger = "enter_testing" if direction == "enter" else "exit_testing"
            updated = _apply_transition(db, ticket, trigger, actor_id)
            return {"status": updated.status, "status_label": STATUS_LABELS[updated.status],
                    "locked_fields": updated.locked_fields()}, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/resolution")
@ns.param("ticket_id", "UUID del ticket")
class TicketResolution(Resource):
    @ns.doc("record_resolution_response")
    @ns.expect(_resolution_input, validate=False)
    @ns.response(200, "Respuesta registrada (aceptar habilita el cierre; rechazar vuelve a EN EJECUCIÓN)", _status_result_out)
    @ns.response(400, "Falta el campo 'accepted'", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:transition", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "El ticket no está en estado Resuelto", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "transition")
    def post(self, ticket_id: str):
        """Aceptación/rechazo de la resolución en nombre del usuario (clarificación Q2)."""
        data = request.get_json(silent=True) or {}
        if "accepted" not in data:
            return {"error": "validation_error", "message": "El campo 'accepted' es requerido"}, 400
        accepted = bool(data["accepted"])
        raw_body = str(data.get("body", "")).strip()
        body = sanitize_html(raw_body) if raw_body else (
            "El usuario aceptó la resolución" if accepted else "El usuario rechazó la resolución")
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            if ticket.status != "resuelto":
                return {"error": "invalid_transition",
                        "message": "Solo se registra la respuesta de resolución en estado Resuelto"}, 409
            actor_id, _, _ = _actor_context(db)
            comment = Comment.create(ticket_id=ticket.id, comment_type="respuesta_usuario",
                                     body=body, author_id=actor_id)
            CommentRepository(db).add(comment, commit=False)
            if accepted:
                TicketRepository(db).update_fields(
                    ticket.id, resolution_accepted_at=datetime.now(timezone.utc))
                db.commit()
                updated = TicketRepository(db).get_by_id(ticket.id)
                return {"status": updated.status, "close_eligible": True}, 200
            # rechazo → vuelve a EN EJECUCIÓN + notificación al resolutor
            new_status = ticket_fsm.apply(ticket.status, "reject_resolution")
            ticket_repo = TicketRepository(db)
            sla_updates = _sla_updates_for_transition(db, ticket, new_status)
            ticket_repo.update_fields(ticket.id, status=new_status, resolution_accepted_at=None,
                                      **sla_updates)
            ticket_repo.add_transition(ticket.id, ticket.status, new_status, actor_id,
                                       comment_id=comment.id, commit=False)
            if ticket.assignee_id:
                assignee = ResourceRepository(db).get_by_id(ticket.assignee_id)
                if assignee and assignee.user_id:
                    NotificationRepository(db).add(
                        _notif_svc.build(assignee.user_id, "resolution_rejected", ticket.id,
                                         ticket.ticket_number), commit=False)
            db.commit()
            updated = TicketRepository(db).get_by_id(ticket.id)
            return {"status": updated.status, "status_label": STATUS_LABELS[updated.status],
                    "locked_fields": updated.locked_fields()}, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/close")
@ns.param("ticket_id", "UUID del ticket")
class TicketClose(Resource):
    @ns.doc("close_ticket")
    @ns.expect(_close_input, validate=False)
    @ns.response(200, "Ticket cerrado", _ticket_detail_out)
    @ns.response(400, "Falta resolution_type_id o body", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso, o ticket no asignado al Resolutor", _error)
    @ns.response(404, "Ticket o tipo de resolución no encontrado", _error)
    @ns.response(409, "No elegible para cerrar (falta aceptación, 3+ días, o sin tiempo "
                      "registrado — OBS-0026, salvo tipo de resolución allow_zero_time)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "transition")
    def post(self, ticket_id: str):
        """Cierre (FR-012): exige tipo de resolución + descripción; notifica Coordinador y QM.

        OBS-0026: exige tiempo registrado en `work_sessions` salvo que el tipo de resolución
        esté marcado `allow_zero_time` (ej. "No es incidente", "Sin respuesta de usuario")."""
        data = request.get_json(silent=True) or {}
        resolution_type_id = parse_uuid(str(data.get("resolution_type_id", "")))
        body = sanitize_html(str(data.get("body", "")))
        if not resolution_type_id:
            return {"error": "validation_error", "message": "El campo 'resolution_type_id' es requerido"}, 400
        if not strip_html(body).strip():
            return {"error": "validation_error",
                    "message": "La descripción de la solución es requerida para cerrar"}, 400
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            actor_id, can_manage, actor_resource_id = _actor_context(db)
            if not can_manage and (actor_resource_id is None or ticket.assignee_id != actor_resource_id):
                return {"error": "forbidden", "message": "Solo puedes cerrar tickets asignados a ti"}, 403
            if not _close_eligible(ticket):
                return {"error": "close_not_allowed",
                        "message": "El cierre requiere aceptación del usuario o 3+ días sin respuesta"}, 409
            resolution_type = CatalogRepository(db, "resolution-types").get_by_id(resolution_type_id)
            if not resolution_type:
                return {"error": "not_found", "message": "Tipo de resolución no encontrado"}, 404
            if not resolution_type.get("allow_zero_time"):
                minutes = WorkSessionRepository(db).sum_minutes_for_ticket(ticket.id)
                if minutes <= 0:
                    return {"error": "no_time_registered",
                            "message": "No se puede cerrar: el ticket no tiene tiempo registrado. "
                                       "Registra tiempo o usa un tipo de resolución que no lo requiera "
                                       "(ej. 'No es incidente')."}, 409

            comment = Comment.create(ticket_id=ticket.id, comment_type="descripcion_solucion",
                                     body=body, author_id=actor_id)
            CommentRepository(db).add(comment, commit=False)
            new_status = ticket_fsm.apply(ticket.status, "close")
            ticket_repo = TicketRepository(db)
            sla_updates = _sla_updates_for_transition(db, ticket, new_status)
            ticket_repo.update_fields(ticket.id, status=new_status,
                                      resolution_type_id=resolution_type_id,
                                      closed_at=datetime.now(timezone.utc), **sla_updates)
            ticket_repo.add_transition(ticket.id, ticket.status, new_status, actor_id,
                                       comment_id=comment.id, commit=False)
            # FR-024: notificar a Coordinadores y QMs activos
            notif_repo = NotificationRepository(db)
            for user in _users_with_roles(db, ("Coordinador", "QM")):
                notif_repo.add(_notif_svc.build(user_id=user, event_type="closed",
                                                ticket_id=ticket.id,
                                                ticket_number=ticket.ticket_number), commit=False)
            db.commit()
            updated = ticket_repo.get_by_id(ticket.id)
            return _ticket_detail(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/cancel")
@ns.param("ticket_id", "UUID del ticket")
class TicketCancel(Resource):
    @ns.doc("cancel_ticket")
    @ns.expect(_cancel_input, validate=False)
    @ns.response(200, "Ticket cancelado", _ticket_detail_out)
    @ns.response(400, "Falta el motivo de cancelación", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:cancel", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "El ticket ya está en un estado final", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "cancel")
    def post(self, ticket_id: str):
        """Cancelar desde cualquier estado no final, con motivo obligatorio."""
        data = request.get_json(silent=True) or {}
        body = sanitize_html(str(data.get("body", "")))
        if not strip_html(body).strip():
            return {"error": "validation_error", "message": "El motivo de cancelación es requerido"}, 400
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            comment = Comment.create(ticket_id=ticket.id, comment_type="cancelacion",
                                     body=body, author_id=g.current_user.id)
            CommentRepository(db).add(comment, commit=False)
            new_status = ticket_fsm.apply(ticket.status, "cancel")
            ticket_repo = TicketRepository(db)
            sla_updates = _sla_updates_for_transition(db, ticket, new_status)
            ticket_repo.update_fields(ticket.id, status=new_status, **sla_updates)
            ticket_repo.add_transition(ticket.id, ticket.status, new_status,
                                       g.current_user.id, comment_id=comment.id, commit=False)
            db.commit()
            updated = ticket_repo.get_by_id(ticket.id)
            return _ticket_detail(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/status")
@ns.param("ticket_id", "UUID de la Tarea o Subtarea")
class TicketStatusChange(Resource):
    @ns.doc("change_task_status")
    @ns.expect(_status_change_input, validate=False)
    @ns.response(200, "Tarea/Subtarea actualizada", _ticket_detail_out)
    @ns.response(400, "status ausente/desconocido, o comment vacío", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:transition", _error)
    @ns.response(404, "Ticket/Tarea no encontrado", _error)
    @ns.response(409, "El registro no es una Tarea (not_a_task), o se intenta cerrar sin tiempo "
                      "registrado (no_time_registered — OBS-0026)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "transition")
    def patch(self, ticket_id: str):
        """Transición libre de estado de una Tarea/Subtarea (spec 009, FR-003/FR-004): cualquier
        estado del catálogo de 10 compartido con Ticket, sin restricción de secuencia, con
        comentario obligatorio. Reemplaza `POST /{id}/task-transition` (spec 008, retirado).

        OBS-0026: transicionar a "cerrado" exige tiempo registrado en `work_sessions` — las
        Tareas no tienen tipo de resolución, así que a diferencia del cierre de Tickets no hay
        excepción `allow_zero_time`."""
        data = request.get_json(silent=True) or {}
        new_status = str(data.get("status", "")).strip()
        comment = sanitize_html(str(data.get("comment", "")))
        if not new_status:
            return {"error": "validation_error", "message": "El campo 'status' es requerido"}, 400
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            if not _is_task(ticket, db):
                raise DomainError(
                    "not_a_task", "Este registro es un Ticket, no una Tarea", status_code=409)
            if not strip_html(comment).strip():
                return {"error": "validation_error",
                        "message": "Debe indicar un comentario que documente el cambio de estado"}, 400
            if new_status == "cerrado" and WorkSessionRepository(db).sum_minutes_for_ticket(ticket.id) <= 0:
                return {"error": "no_time_registered",
                        "message": "No se puede cerrar: la Tarea no tiene tiempo registrado."}, 409
            _svc.free_transition_task(
                ticket, new_status, comment, g.current_user.id,
                tickets_repo=TicketRepository(db), comments_repo=CommentRepository(db),
            )
            updated = TicketRepository(db).get_by_id(ticket.id)
            return _ticket_detail(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:ticket_id>/attachments/<string:attachment_id>")
@ns.param("ticket_id", "UUID del ticket")
@ns.param("attachment_id", "UUID del adjunto")
class TicketAttachment(Resource):
    @ns.doc("download_attachment")
    @ns.produces(["application/octet-stream"])
    @ns.response(200, "Archivo (stream binario con el content-type original)")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:view", _error)
    @ns.response(404, "Adjunto no encontrado o ruta inválida", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "view")
    def get(self, ticket_id: str, attachment_id: str):
        """Descarga autenticada de un adjunto"""
        aid = parse_uuid(attachment_id)
        if not aid:
            return {"error": "validation_error", "message": "ID de adjunto inválido"}, 400
        try:
            db = get_db()
            attachment = CommentRepository(db).get_attachment(aid)
            if not attachment:
                return {"error": "not_found", "message": "Adjunto no encontrado"}, 404
            path = attachment_storage.open_path(attachment.storage_path)
            return send_file(path, mimetype=attachment.content_type,
                             as_attachment=True, download_name=attachment.filename)
        except attachment_storage.AttachmentError as e:
            return {"error": "attachment_error", "message": e.message}, 404
        except Exception:
            return server_error()


def _users_with_roles(db, role_names: tuple[str, ...]) -> list[uuid.UUID]:
    from backend.infra.models.user_model import UserModel
    from backend.infra.models.role_model import RoleModel
    rows = (db.query(UserModel.id)
            .join(RoleModel, UserModel.role_id == RoleModel.id)
            .filter(RoleModel.name.in_(role_names), UserModel.active.is_(True))
            .all())
    return [row[0] for row in rows]
