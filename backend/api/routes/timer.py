"""Rutas del cronómetro manual de tiempo (spec 012, provisional; contracts/timer.md).

Todas exigen JWT + permiso `work_sessions:manage` (el mismo que ya habilita la carga manual de
tiempo — no se crea un permiso nuevo). El `resource_id` efectivo se resuelve **siempre** del
usuario autenticado; a diferencia de `work_sessions`, ningún endpoint acepta `resource_id` en
query/body — el cronómetro es personal, sin variante "para otro recurso" (FR-005).
"""
from datetime import datetime, timezone

from flask import g, request
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.errors import DomainError
from backend.domain.services.ticket_timer_service import TicketTimerService, STALE_THRESHOLD_SECONDS
from backend.infra.database import get_db
from backend.infra.repositories.catalog_repo import CatalogRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.ticket_repo import TicketRepository
from backend.infra.repositories.ticket_timer_repo import TicketTimerRepository
from backend.infra.repositories.work_session_repo import WorkSessionRepository

ns = Namespace("timer", description="Cronómetro manual de tiempo por recurso (provisional)",
              path="/api/timer")

_svc = TicketTimerService()

_error = error_model(ns, "TimerError")

_timer_out = ns.model("Timer", {
    "status": fields.String(enum=["inactive", "running", "paused"]),
    "ticket_id": fields.String(allow_null=True),
    "ticket_number": fields.String(allow_null=True),
    "total_seconds": fields.Integer(),
    "running_seconds": fields.Integer(),
    "stale": fields.Boolean(description="true si lleva corriendo sin pausar más de "
                                        f"{STALE_THRESHOLD_SECONDS // 3600} horas (FR-010)"),
})

_timer_start_input = ns.model("TimerStartInput", {
    "ticket_id": fields.String(required=True),
})

_timer_finish_input = ns.model("TimerFinishInput", {
    "note": fields.String(description="Opcional, se pasa al Registro de tiempo generado"),
})


def _is_task(ticket, db) -> bool:
    record_type = CatalogRepository(db, "record-types").get_by_id(ticket.record_type_id)
    return bool(record_type and record_type["name"] == "Tarea")


def _resolve_resource(db):
    resource = ResourceRepository(db).get_by_user_id(g.current_user.id)
    if not resource:
        raise DomainError("no_resource_profile", "El usuario no tiene un recurso asociado", status_code=400)
    return resource


def _serialize(timer, db) -> dict:
    now = datetime.now(timezone.utc)
    ticket = TicketRepository(db).get_by_id(timer.ticket_id) if timer.ticket_id else None
    running_seconds = timer.running_seconds(now)
    return {
        "status": timer.status,
        "ticket_id": str(timer.ticket_id) if timer.ticket_id else None,
        "ticket_number": ticket.number_display if ticket else None,
        "total_seconds": timer.total_seconds(now),
        "running_seconds": running_seconds,
        "stale": running_seconds > STALE_THRESHOLD_SECONDS,
    }


@ns.route("")
class TimerCurrent(Resource):
    @ns.doc("get_current_timer")
    @ns.response(200, "Cronómetro actual del recurso autenticado (a lo sumo uno)", _timer_out)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:manage", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def get(self):
        """Cronómetro **propio** del usuario autenticado. No admite parámetros para consultar
        el cronómetro de otro recurso (FR-005) — a diferencia de `GET /api/work-sessions`, no
        existe aquí una variante `view_all`."""
        db = get_db()
        try:
            resource = _resolve_resource(db)
            timer = TicketTimerRepository(db).get_by_resource(resource.id)
            return _serialize(timer, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/start")
class TimerStart(Resource):
    @ns.doc("start_timer")
    @ns.expect(_timer_start_input, validate=False)
    @ns.response(201, "Cronómetro iniciado", _timer_out)
    @ns.response(400, "ticket_id ausente o inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:manage, o el recurso no participa del ticket", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "Ya hay un cronómetro activo en otro ticket (timer_already_active)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def post(self):
        """Inicia el cronómetro del recurso autenticado. Siempre opera sobre el propio
        `resource_id` resuelto del JWT — no acepta `resource_id` en el body."""
        data = request.get_json(silent=True) or {}
        ticket_id = parse_uuid(data.get("ticket_id") or "")
        if not ticket_id:
            return {"error": "validation_error", "message": "ticket_id inválido"}, 400

        db = get_db()
        try:
            resource = _resolve_resource(db)
            ticket = TicketRepository(db).get_by_id(ticket_id)
            if not ticket:
                return {"error": "not_found", "message": "Ticket no encontrado"}, 404
            timer = _svc.start(
                resource_id=resource.id, ticket=ticket,
                timer_repo=TicketTimerRepository(db), tickets_repo=TicketRepository(db),
                is_task=_is_task(ticket, db), resources_repo=ResourceRepository(db),
            )
            return _serialize(timer, db), 201
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/pause")
class TimerPause(Resource):
    @ns.doc("pause_timer")
    @ns.response(200, "Cronómetro pausado", _timer_out)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:manage", _error)
    @ns.response(409, "No hay cronómetro corriendo (no_active_timer)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def post(self):
        db = get_db()
        try:
            resource = _resolve_resource(db)
            timer = _svc.pause(resource_id=resource.id, timer_repo=TicketTimerRepository(db))
            return _serialize(timer, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/resume")
class TimerResume(Resource):
    @ns.doc("resume_timer")
    @ns.response(200, "Cronómetro reanudado", _timer_out)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:manage", _error)
    @ns.response(409, "No hay cronómetro pausado (no_paused_timer)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def post(self):
        db = get_db()
        try:
            resource = _resolve_resource(db)
            timer = _svc.resume(resource_id=resource.id, timer_repo=TicketTimerRepository(db))
            return _serialize(timer, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/finish")
class TimerFinish(Resource):
    @ns.doc("finish_timer")
    @ns.expect(_timer_finish_input, validate=False)
    @ns.response(201, "Registro de tiempo creado a partir del cronómetro")
    @ns.response(400, "Límite diario superado (daily_limit_exceeded, mismo código que la carga manual)", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:manage", _error)
    @ns.response(404, "No hay cronómetro activo para el recurso", _error)
    @ns.response(409, "Duración menor a un minuto (duration_too_short), o ticket cerrado (ticket_closed)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def post(self):
        data = request.get_json(silent=True) or {}
        db = get_db()
        try:
            resource = _resolve_resource(db)
            timer = TicketTimerRepository(db).get_by_resource(resource.id)
            is_task = False
            if timer.ticket_id:
                ticket = TicketRepository(db).get_by_id(timer.ticket_id)
                is_task = _is_task(ticket, db) if ticket else False
            work_session = _svc.finish(
                resource_id=resource.id, created_by=g.current_user.id,
                timer_repo=TicketTimerRepository(db), tickets_repo=TicketRepository(db),
                work_sessions_repo=WorkSessionRepository(db), note=data.get("note"),
                is_task=is_task, resources_repo=ResourceRepository(db),
            )
            from backend.api.routes.work_sessions import _serialize as _serialize_work_session
            return _serialize_work_session(work_session, db), 201, \
                {"Location": f"/api/work-sessions/{work_session.id}"}
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
