"""Rutas de tickets: CRUD, Triage Push, ciclo de vida por comentarios, cierre y cancelación.

Todas exigen JWT + permiso del módulo `tickets` (FR-022). Las operaciones que cambian
estado son atómicas: comentario + transición + notificación en la misma transacción
(Decisión 2 de research.md).
"""
from datetime import datetime, timedelta, timezone
import uuid

from flask import g, request, send_file
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission, current_user_has
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.comment import Comment, Attachment, COMMENT_TYPE_LABELS
from backend.domain.entities.ticket import Ticket, STATUS_LABELS
from backend.domain.errors import DomainError
from backend.domain.fsm import ticket_fsm
from backend.domain.services.assignment_service import AssignmentService
from backend.domain.services.comment_service import CommentService
from backend.domain.services.notification_service import NotificationService
from backend.domain.services.ticket_service import TicketService, TicketValidationError
from backend.infra.database import get_db
from backend.infra.repositories.catalog_repo import CatalogRepository
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.comment_repo import CommentRepository
from backend.infra.repositories.notification_repo import NotificationRepository
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.ticket_repo import TicketRepository
from backend.infra.storage import attachments as attachment_storage

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
    "ticket_type": fields.String(required=True, description="incident | evolutive | preventive"),
    "priority": fields.String(required=True, description="critical | high | medium | low"),
    "severity": fields.String(required=True, description="s1 | s2 | s3 | s4"),
    "client_id": fields.String(required=True),
    "project_id": fields.String(description="Opcional: proyecto activo del cliente"),
    "tool_id": fields.String(description="Catálogo herramienta"),
    "process_id": fields.String(description="Catálogo proceso"),
    "escalation_level": fields.String(description="n1..n4 (default n2)"),
    "related_ticket_id": fields.String(description="Ticket relacionado"),
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

_entity_ref = ns.model("EntityRef", {
    "id": fields.String(description="UUID"),
    "name": fields.String(description="Nombre"),
})

_resource_ref = ns.model("ResourceRef", {
    "id": fields.String(description="UUID del recurso"),
    "full_name": fields.String(description="Nombre completo"),
})

_ticket_out = ns.model("Ticket", {
    "id": fields.String(description="UUID del ticket"),
    "ticket_number": fields.String(description="Consecutivo legible", example="TK-000123"),
    "record_type": fields.String(description="ticket | task (task reservado a Fase 3)"),
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
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
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

_ticket_detail_out = ns.inherit("TicketDetail", _ticket_out, {
    "description": fields.String(),
    "tool_id": fields.String(allow_null=True),
    "process_id": fields.String(allow_null=True),
    "resolution_type_id": fields.String(allow_null=True),
    "related_ticket_id": fields.String(allow_null=True),
    "created_by": fields.String(description="UUID de quien creó el ticket"),
    "resolved_at": fields.String(allow_null=True),
    "resolution_accepted_at": fields.String(allow_null=True),
    "closed_at": fields.String(allow_null=True),
    "locked_fields": fields.List(fields.String(), description="Campos no editables en el estado actual (FR-010)"),
    "close_eligible": fields.Boolean(description="true si acepta cierre (aceptado o 3+ días resuelto)"),
    "valid_actions": fields.List(fields.String(), description="Triggers FSM ejecutables desde el estado actual"),
    "comments": fields.List(fields.Nested(_comment_out)),
    "transitions": fields.List(fields.Nested(_transition_out)),
    "assignments": fields.List(fields.Nested(_assignment_out)),
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


def _ticket_summary(ticket: Ticket, db) -> dict:
    client = ClientRepository(db).get_by_id(ticket.client_id)
    project = ProjectRepository(db).get_by_id(ticket.project_id) if ticket.project_id else None
    assignee = ResourceRepository(db).get_by_id(ticket.assignee_id) if ticket.assignee_id else None
    return {
        "id": str(ticket.id),
        "ticket_number": ticket.number_display,
        "record_type": ticket.record_type,
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
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }


def _ticket_detail(ticket: Ticket, db) -> dict:
    d = _ticket_summary(ticket, db)
    d.update({
        "description": ticket.description,
        "tool_id": str(ticket.tool_id) if ticket.tool_id else None,
        "process_id": str(ticket.process_id) if ticket.process_id else None,
        "estimated_resolution_minutes": ticket.estimated_resolution_minutes,
        "resolution_type_id": str(ticket.resolution_type_id) if ticket.resolution_type_id else None,
        "related_ticket_id": str(ticket.related_ticket_id) if ticket.related_ticket_id else None,
        "created_by": str(ticket.created_by),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "resolution_accepted_at": ticket.resolution_accepted_at.isoformat() if ticket.resolution_accepted_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "locked_fields": ticket.locked_fields(),
        "close_eligible": _close_eligible(ticket),
        "valid_actions": ticket_fsm.valid_triggers(ticket.status),
        "comments": [_comment_to_dict(c) for c in CommentRepository(db).list_for_ticket(ticket.id)],
        "transitions": TicketRepository(db).list_transitions(ticket.id),
        "assignments": TicketRepository(db).list_assignments(ticket.id),
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


def _apply_transition(db, ticket: Ticket, trigger: str, actor_id: uuid.UUID,
                      comment_id: uuid.UUID | None = None,
                      extra_fields: dict | None = None) -> Ticket:
    """Ejecuta la transición FSM y registra el histórico (sin commit)."""
    new_status = ticket_fsm.apply(ticket.status, trigger)
    repo = TicketRepository(db)
    fields_to_set = {"status": new_status, **(extra_fields or {})}
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
        "sort": {"description": "created_at | -created_at | priority | status (default -created_at)", "type": "string"},
    })
    @ns.response(200, "Listado de tickets", _ticket_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:view", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "view")
    def get(self):
        """Listado paginado con filtros combinables"""
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        statuses = request.args.getlist("status") or None
        try:
            db = get_db()
            items, total = TicketRepository(db).list_paginated(
                page=page, page_size=page_size,
                search=request.args.get("search", "").strip() or None,
                client_id=parse_uuid(request.args.get("client_id") or "") or None,
                project_id=parse_uuid(request.args.get("project_id") or "") or None,
                statuses=statuses,
                priority=request.args.get("priority") or None,
                severity=request.args.get("severity") or None,
                ticket_type=request.args.get("ticket_type") or None,
                assignee_id=parse_uuid(request.args.get("assignee_id") or "") or None,
                escalation_level=request.args.get("escalation_level") or None,
                sort=request.args.get("sort", "-created_at"),
            )
            return {"items": [_ticket_summary(t, db) for t in items],
                    "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_ticket")
    @ns.expect(_ticket_input, validate=False)
    @ns.response(201, "Ticket creado (nace en estado NUEVO)", _ticket_detail_out)
    @ns.response(400, "Datos inválidos o enum desconocido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:create", _error)
    @ns.response(404, "Cliente, proyecto o catálogo no encontrado", _error)
    @ns.response(409, "Cliente/proyecto/catálogo inactivo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "create")
    def post(self):
        """Crear un ticket (nace en NUEVO con consecutivo, FR-001/002)"""
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        for field_name in ("title", "description", "ticket_type", "priority", "severity", "client_id"):
            if not data.get(field_name):
                return {"error": "validation_error", "message": f"El campo '{field_name}' es requerido"}, 400
        client_id = parse_uuid(data["client_id"])
        if not client_id:
            return {"error": "validation_error", "message": "client_id inválido"}, 400
        project_id = parse_uuid(data["project_id"]) if data.get("project_id") else None
        tool_id = parse_uuid(data["tool_id"]) if data.get("tool_id") else None
        process_id = parse_uuid(data["process_id"]) if data.get("process_id") else None
        related_id = parse_uuid(data["related_ticket_id"]) if data.get("related_ticket_id") else None
        try:
            db = get_db()
            _svc.validate_enums(data)
            _svc.validate_create(
                client_id=client_id, project_id=project_id, tool_id=tool_id,
                process_id=process_id, related_ticket_id=related_id,
                clients_repo=ClientRepository(db), projects_repo=ProjectRepository(db),
                tools_repo=CatalogRepository(db, "tools"),
                processes_repo=CatalogRepository(db, "processes"),
                tickets_repo=TicketRepository(db),
            )
            ticket = Ticket(
                id=uuid.uuid4(), ticket_number=0,  # lo asigna la secuencia
                title=str(data["title"]).strip(), description=str(data["description"]).strip(),
                ticket_type=data["ticket_type"], priority=data["priority"],
                severity=data["severity"], client_id=client_id,
                escalation_level=data.get("escalation_level") or "n2",
                project_id=project_id, tool_id=tool_id, process_id=process_id,
                related_ticket_id=related_id, created_by=g.current_user.id,
            )
            created = TicketRepository(db).create(ticket)
            return _ticket_detail(created, db), 201, {"Location": f"/api/tickets/{created.id}"}
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
    @ns.response(403, "Sin permiso tickets:view", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "view")
    def get(self, ticket_id: str):
        """Detalle completo: campos, locked_fields, close_eligible, historiales"""
        try:
            db = get_db()
            ticket, err = _get_ticket_or_404(db, ticket_id)
            if err:
                return err
            return _ticket_detail(ticket, db), 200
        except Exception:
            return server_error()

    @ns.doc("update_ticket")
    @ns.response(200, "Ticket actualizado", _ticket_detail_out)
    @ns.response(400, "Datos inválidos, campo desconocido o intento de editar `status`", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:edit", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "Campo bloqueado por el estado actual (`field_locked`)", _error)
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
            clean = _svc.validate_patch(ticket, dict(data))
            for uuid_field in ("tool_id", "process_id", "related_ticket_id"):
                if uuid_field in clean and clean[uuid_field] is not None:
                    parsed = parse_uuid(str(clean[uuid_field]))
                    if not parsed:
                        return {"error": "validation_error", "message": f"{uuid_field} inválido"}, 400
                    clean[uuid_field] = parsed
            updated = TicketRepository(db).update_fields(ticket.id, **clean)
            return _ticket_detail(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
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
            ticket_repo.update_fields(ticket.id, status=new_status, assignee_id=assignee_id)
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
        "campos `files` (máx 10 MB c/u, tipos permitidos). Los tipos con efecto de "
        "transición (confirmacion_atencion, solicitud_informacion, termina_analisis, "
        "solicitud_cierre, respuesta_usuario) mueven el ticket en la misma operación."
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
        else:
            data = request.get_json(silent=True) or {}
            comment_type = data.get("comment_type", "")
            body = data.get("body", "")
            files = []
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

            updated = ticket
            if trigger is not None:
                extra: dict = {}
                if trigger == "solicitud_cierre":
                    extra["resolved_at"] = datetime.now(timezone.utc)
                    extra["resolution_accepted_at"] = None
                new_status = ticket_fsm.apply(ticket.status, trigger)
                ticket_repo = TicketRepository(db)
                ticket_repo.update_fields(ticket.id, status=new_status, **extra)
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
        body = str(data.get("body", "")).strip() or (
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
            ticket_repo.update_fields(ticket.id, status=new_status, resolution_accepted_at=None)
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
    @ns.response(409, "No elegible para cerrar (falta aceptación o 3+ días)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "transition")
    def post(self, ticket_id: str):
        """Cierre (FR-012): exige tipo de resolución + descripción; notifica Coordinador y QM."""
        data = request.get_json(silent=True) or {}
        resolution_type_id = parse_uuid(str(data.get("resolution_type_id", "")))
        body = str(data.get("body", "")).strip()
        if not resolution_type_id:
            return {"error": "validation_error", "message": "El campo 'resolution_type_id' es requerido"}, 400
        if not body:
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

            comment = Comment.create(ticket_id=ticket.id, comment_type="descripcion_solucion",
                                     body=body, author_id=actor_id)
            CommentRepository(db).add(comment, commit=False)
            new_status = ticket_fsm.apply(ticket.status, "close")
            ticket_repo = TicketRepository(db)
            ticket_repo.update_fields(ticket.id, status=new_status,
                                      resolution_type_id=resolution_type_id,
                                      closed_at=datetime.now(timezone.utc))
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
        body = str(data.get("body", "")).strip()
        if not body:
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
            ticket_repo.update_fields(ticket.id, status=new_status)
            ticket_repo.add_transition(ticket.id, ticket.status, new_status,
                                       g.current_user.id, comment_id=comment.id, commit=False)
            db.commit()
            updated = ticket_repo.get_by_id(ticket.id)
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
