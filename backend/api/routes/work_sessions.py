"""Rutas de registro diario de tiempos (Fase 2, contracts/work-sessions.md).

Todas exigen JWT + permiso del módulo `work_sessions`. Un recurso sin `view_all`/`manage_all`
solo puede ver/gestionar sus propios registros — el `resource_id` efectivo se resuelve del
usuario autenticado, nunca se confía en lo que envía el cliente salvo para Admin.
"""
from datetime import date, datetime, timedelta
import uuid

from flask import g, request
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission, current_user_has
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.errors import DomainError
from backend.domain.services.work_session_service import WorkSessionService
from backend.infra.database import get_db
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.ticket_repo import TicketRepository
from backend.infra.repositories.work_session_repo import WorkSessionRepository

ns = Namespace("work-sessions", description="Registro diario de tiempos por recurso",
              path="/api/work-sessions")

_svc = WorkSessionService()

MAX_SUMMARY_RANGE_DAYS = 92

# ── Swagger models ────────────────────────────────────────────────────────────

_error = error_model(ns, "WorkSessionError")

_work_session_input = ns.model("WorkSessionInput", {
    "ticket_id": fields.String(required=True),
    "work_date": fields.String(required=True, description="ISO-8601 (YYYY-MM-DD)"),
    "duration_minutes": fields.Integer(description="Requerido si no se envían started_at/ended_at"),
    "started_at": fields.String(description="ISO-8601 con hora; si viene junto con ended_at, "
                                             "la duración se calcula y se ignora duration_minutes"),
    "ended_at": fields.String(description="ISO-8601 con hora"),
    "note": fields.String(),
    "resource_id": fields.String(description="Solo Admin (work_sessions:manage_all): registrar "
                                              "en nombre de otro recurso"),
})

_work_session_patch_input = ns.model("WorkSessionPatchInput", {
    "duration_minutes": fields.Integer(),
    "started_at": fields.String(),
    "ended_at": fields.String(),
    "note": fields.String(),
})

_work_session_out = ns.model("WorkSession", {
    "id": fields.String(),
    "resource_id": fields.String(),
    "resource_name": fields.String(),
    "ticket_id": fields.String(),
    "ticket_number": fields.String(),
    "work_date": fields.String(),
    "duration_minutes": fields.Integer(),
    "started_at": fields.String(allow_null=True),
    "ended_at": fields.String(allow_null=True),
    "note": fields.String(allow_null=True),
    "created_by": fields.String(),
    "updated_by": fields.String(allow_null=True),
    "created_at": fields.String(),
    "updated_at": fields.String(),
})

_work_session_list_out = ns.model("WorkSessionList", {
    "items": fields.List(fields.Nested(_work_session_out)),
    "total": fields.Integer(),
})

_daily_summary_out = ns.model("WorkSessionDailySummary", {
    "resource_id": fields.String(),
    "resource_name": fields.String(),
    "range": fields.Raw(),
    "days": fields.List(fields.Raw()),
    "total_minutes": fields.Integer(),
})

_resources_overview_out = ns.model("WorkSessionResourcesOverview", {
    "range": fields.Raw(),
    "resources": fields.List(fields.Raw()),
})


def _parse_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise DomainError("validation_error", f"'{field_name}' debe tener formato YYYY-MM-DD",
                          status_code=400)


def _parse_datetime(value, field_name: str):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        raise DomainError("validation_error", f"'{field_name}' debe ser una fecha/hora ISO-8601 válida",
                          status_code=400)


def _parse_summary_range(args) -> tuple[date, date]:
    """Valida `date_from`/`date_to` (requeridos, orden correcto, rango máximo) — compartido por
    `/summary` y `/summary/overview`."""
    if not args.get("date_from") or not args.get("date_to"):
        raise DomainError("validation_error", "date_from y date_to son requeridos", status_code=400)
    date_from = _parse_date(args["date_from"], "date_from")
    date_to = _parse_date(args["date_to"], "date_to")
    if date_to < date_from:
        raise DomainError("validation_error", "date_to no puede ser anterior a date_from", status_code=400)
    if (date_to - date_from).days > MAX_SUMMARY_RANGE_DAYS:
        raise DomainError("validation_error",
                          f"El rango no puede superar {MAX_SUMMARY_RANGE_DAYS} días", status_code=400)
    return date_from, date_to


def _serialize(ws, db) -> dict:
    resource = ResourceRepository(db).get_by_id(ws.resource_id)
    ticket = TicketRepository(db).get_by_id(ws.ticket_id)
    return {
        "id": str(ws.id),
        "resource_id": str(ws.resource_id),
        "resource_name": resource.full_name if resource else None,
        "ticket_id": str(ws.ticket_id),
        "ticket_number": ticket.number_display if ticket else None,
        "work_date": ws.work_date.isoformat(),
        "duration_minutes": ws.duration_minutes,
        "started_at": ws.started_at.isoformat() if ws.started_at else None,
        "ended_at": ws.ended_at.isoformat() if ws.ended_at else None,
        "note": ws.note,
        "created_by": str(ws.created_by),
        "updated_by": str(ws.updated_by) if ws.updated_by else None,
        "created_at": ws.created_at.isoformat(),
        "updated_at": ws.updated_at.isoformat(),
    }


# ── Rutas ─────────────────────────────────────────────────────────────────────

@ns.route("")
class WorkSessionList(Resource):
    @ns.doc("list_work_sessions", params={
        "resource_id": {"description": "Solo con permiso work_sessions:view_all", "type": "string"},
        "ticket_id": {"type": "string"},
        "date_from": {"type": "string"}, "date_to": {"type": "string"},
        "page": {"type": "integer", "default": 1}, "page_size": {"type": "integer", "default": 20},
    })
    @ns.response(200, "Listado de registros", _work_session_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:view_own", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "view_own")
    def get(self):
        db = get_db()
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400

        resource_id = parse_uuid(request.args.get("resource_id") or "") or None
        if not current_user_has("work_sessions", "view_all"):
            resource_id = ResourceRepository(db).get_by_user_id(g.current_user.id)
            resource_id = resource_id.id if resource_id else uuid.uuid4()  # sin recurso → sin resultados

        ticket_id = parse_uuid(request.args.get("ticket_id") or "") or None
        date_from = _parse_date(request.args["date_from"], "date_from") if request.args.get("date_from") else None
        date_to = _parse_date(request.args["date_to"], "date_to") if request.args.get("date_to") else None
        try:
            items, total = WorkSessionRepository(db).list_by_filters(
                resource_id=resource_id, ticket_id=ticket_id, date_from=date_from, date_to=date_to,
                page=page, page_size=page_size,
            )
            return {"items": [_serialize(ws, db) for ws in items], "total": total}, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()

    @ns.doc("create_work_session")
    @ns.expect(_work_session_input, validate=False)
    @ns.response(201, "Registro creado", _work_session_out)
    @ns.response(400, "Datos inválidos, fecha futura, o límite diario superado", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:manage, o el recurso no participa del ticket", _error)
    @ns.response(404, "Ticket no encontrado", _error)
    @ns.response(409, "El ticket está cerrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def post(self):
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        for field_name in ("ticket_id", "work_date"):
            if data.get(field_name) is None:
                return {"error": "validation_error", "message": f"El campo '{field_name}' es requerido"}, 400
        ticket_id = parse_uuid(data["ticket_id"])
        if not ticket_id:
            return {"error": "validation_error", "message": "ticket_id inválido"}, 400
        duration_minutes = None
        if data.get("duration_minutes") is not None:
            try:
                duration_minutes = int(data["duration_minutes"])
            except (TypeError, ValueError):
                return {"error": "validation_error", "message": "duration_minutes debe ser un entero"}, 400

        db = get_db()
        allow_any = current_user_has("work_sessions", "manage_all")
        resource_id = None
        if allow_any and data.get("resource_id"):
            resource_id = parse_uuid(data["resource_id"])
        if resource_id is None:
            own = ResourceRepository(db).get_by_user_id(g.current_user.id)
            if not own:
                return {"error": "no_resource_profile",
                        "message": "El usuario no tiene un recurso asociado"}, 400
            resource_id = own.id
        try:
            work_date = _parse_date(data["work_date"], "work_date")
            started_at = _parse_datetime(data.get("started_at"), "started_at")
            ended_at = _parse_datetime(data.get("ended_at"), "ended_at")
            ticket = TicketRepository(db).get_by_id(ticket_id)
            if not ticket:
                return {"error": "not_found", "message": "Ticket no encontrado"}, 404
            created = _svc.create(
                resource_id=resource_id, ticket=ticket, work_date=work_date,
                duration_minutes=duration_minutes, created_by=g.current_user.id,
                work_sessions_repo=WorkSessionRepository(db), tickets_repo=TicketRepository(db),
                note=data.get("note"), started_at=started_at, ended_at=ended_at,
                allow_any=allow_any,
            )
            return _serialize(created, db), 201, {"Location": f"/api/work-sessions/{created.id}"}
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/summary")
class WorkSessionSummary(Resource):
    @ns.doc("work_sessions_summary", params={
        "resource_id": {"description": "Solo con permiso work_sessions:view_all", "type": "string"},
        "date_from": {"type": "string", "required": True}, "date_to": {"type": "string", "required": True},
    })
    @ns.response(200, "Resumen diario de un único recurso (propio, o explícito con view_all)", _daily_summary_out)
    @ns.response(400, "Rango de fechas inválido, o falta resource_id (ver /summary/overview)", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:view_own", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "view_own")
    def get(self):
        """Resumen diario de **un solo recurso** — forma de respuesta fija (`_daily_summary_out`).
        Para ver todos los recursos a la vez, usar `GET /api/work-sessions/summary/overview`
        (contrato separado en vez de una segunda forma de respuesta bajo el mismo endpoint)."""
        db = get_db()
        try:
            date_from, date_to = _parse_summary_range(request.args)
        except DomainError as e:
            return {"error": e.code, "message": e.message}, e.status_code

        has_view_all = current_user_has("work_sessions", "view_all")
        resource_id = parse_uuid(request.args.get("resource_id") or "") or None
        try:
            if resource_id and not has_view_all:
                resource_id = None  # se ignora, se fuerza al propio (contrato)
            if resource_id is None:
                own = ResourceRepository(db).get_by_user_id(g.current_user.id)
                if own:
                    resource_id = own.id
                elif has_view_all:
                    return {"error": "validation_error",
                            "message": "Especificá resource_id, o usá "
                                       "GET /api/work-sessions/summary/overview para ver todos "
                                       "los recursos"}, 400
                else:
                    return {"resource_id": None, "range": {"date_from": date_from.isoformat(),
                            "date_to": date_to.isoformat()}, "days": [], "total_minutes": 0}, 200
            repo = WorkSessionRepository(db)
            summary = _svc.get_daily_summary(
                resource_id=resource_id, date_from=date_from, date_to=date_to,
                work_sessions_repo=repo)
            resource = ResourceRepository(db).get_by_id(resource_id)
            return {
                "resource_id": str(resource_id),
                "resource_name": resource.full_name if resource else None,
                "range": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
                "days": [{"work_date": d["work_date"].isoformat(),
                          "total_minutes": d["total_minutes"],
                          "sin_registro": d["sin_registro"]} for d in summary["days"]],
                "total_minutes": summary["total_minutes"],
            }, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/summary/overview")
class WorkSessionSummaryOverview(Resource):
    @ns.doc("work_sessions_summary_overview", params={
        "date_from": {"type": "string", "required": True}, "date_to": {"type": "string", "required": True},
    })
    @ns.response(200, "Total del rango por cada recurso — forma de respuesta fija, distinta de "
                      "/summary", _resources_overview_out)
    @ns.response(400, "Rango de fechas inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso work_sessions:view_all", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "view_all")
    def get(self):
        """Resumen del rango para **todos los recursos a la vez** (Coordinador/QM/Admin, FR
        spec 004 US2) — endpoint separado de `/summary` en vez de una segunda forma de
        respuesta bajo la misma URL."""
        db = get_db()
        try:
            date_from, date_to = _parse_summary_range(request.args)
            repo = WorkSessionRepository(db)
            overview = _svc.get_all_resources_summary(date_from=date_from, date_to=date_to,
                                                       work_sessions_repo=repo)
            for row in overview:
                resource = ResourceRepository(db).get_by_id(row["resource_id"])
                row["resource_id"] = str(row["resource_id"])
                row["resource_name"] = resource.full_name if resource else None
            return {"range": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
                    "resources": overview}, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:work_session_id>")
@ns.param("work_session_id", "UUID del registro de tiempo")
class WorkSessionDetail(Resource):
    @ns.doc("update_work_session")
    @ns.expect(_work_session_patch_input, validate=False)
    @ns.response(200, "Registro actualizado", _work_session_out)
    @ns.response(400, "UUID inválido o datos inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "No es el dueño del registro, o ventana de edición expirada", _error)
    @ns.response(404, "Registro no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def patch(self, work_session_id):
        ws_id = parse_uuid(work_session_id)
        if not ws_id:
            return {"error": "validation_error", "message": "work_session_id inválido"}, 400
        data = request.get_json(silent=True) or {}
        db = get_db()
        repo = WorkSessionRepository(db)
        existing = repo.get_by_id(ws_id)
        if not existing:
            return {"error": "not_found", "message": "Registro no encontrado"}, 404
        allow_any = current_user_has("work_sessions", "manage_all")
        if not allow_any:
            own = ResourceRepository(db).get_by_user_id(g.current_user.id)
            if not own or existing.resource_id != own.id:
                return {"error": "forbidden", "message": "No sos el dueño de este registro"}, 403
        duration_minutes = None
        if data.get("duration_minutes") is not None:
            try:
                duration_minutes = int(data["duration_minutes"])
            except (TypeError, ValueError):
                return {"error": "validation_error", "message": "duration_minutes debe ser un entero"}, 400
        try:
            started_at = _parse_datetime(data.get("started_at"), "started_at")
            ended_at = _parse_datetime(data.get("ended_at"), "ended_at")
            updated = _svc.update(
                existing=existing, actor_id=g.current_user.id, work_sessions_repo=repo,
                duration_minutes=duration_minutes, note=data.get("note"),
                started_at=started_at, ended_at=ended_at, allow_any=allow_any,
            )
            return _serialize(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()

    @ns.doc("delete_work_session")
    @ns.response(204, "Eliminado")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "No es el dueño del registro, o ventana de edición expirada", _error)
    @ns.response(404, "Registro no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("work_sessions", "manage")
    def delete(self, work_session_id):
        ws_id = parse_uuid(work_session_id)
        if not ws_id:
            return {"error": "validation_error", "message": "work_session_id inválido"}, 400
        db = get_db()
        repo = WorkSessionRepository(db)
        existing = repo.get_by_id(ws_id)
        if not existing:
            return {"error": "not_found", "message": "Registro no encontrado"}, 404
        allow_any = current_user_has("work_sessions", "manage_all")
        if not allow_any:
            own = ResourceRepository(db).get_by_user_id(g.current_user.id)
            if not own or existing.resource_id != own.id:
                return {"error": "forbidden", "message": "No sos el dueño de este registro"}, 403
        try:
            _svc.delete(existing=existing, actor_id=g.current_user.id, work_sessions_repo=repo,
                       allow_any=allow_any)
            return "", 204
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
