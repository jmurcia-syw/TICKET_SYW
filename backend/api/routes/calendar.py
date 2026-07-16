"""Fase 5 (spec 020): calendarios, festivos, horario laboral, ausencias y disponibilidad.

Esta sesión implementa el MVP (Historia 1 — disponibilidad, FR-013 a FR-016), la Historia 2
(solicitud y aprobación en cadena de ausencias — Jefe directo + RRHH, FR-008 a FR-012a), la
Historia 3 (festivos por país, FR-001/002/004/005) y la Historia 4 (horario laboral semanal,
FR-006).
"""
import uuid
from datetime import date, datetime, time, timezone as dt_timezone

from flask import g, request, send_file
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import current_user_has, enforce_module, require_authenticated, require_permission
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.calendar import AbsenceRequest, AbsenceRequestAttachment, Holiday, WorkScheduleSlot
from backend.domain.services import absence_service
from backend.domain.services.availability_service import (
    DEFAULT_END_TIME, DEFAULT_START_TIME, DEFAULT_WEEKDAYS, compute_availability,
)
from backend.infra.database import get_db
from backend.infra.external.holiday_sync_service import sync_country
from backend.infra.models.resource_model import ResourceModel
from backend.infra.repositories.calendar_repo import (
    HolidayRepository, HolidaySyncStatusRepository, WorkScheduleRepository, AbsenceRequestRepository,
)
from backend.infra.repositories.catalog_repo import CatalogRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.storage import attachments as attachment_storage

ns = Namespace(
    "calendar",
    description="Calendarios, festivos, horario laboral, ausencias y disponibilidad (Fase 5)",
    path="/api",
)

_error = error_model(ns, "CalendarError")
_FORBIDDEN = ({"error": "forbidden", "message": "Acceso denegado"}, 403)

_availability_item = ns.model("AvailabilityItem", {
    "resource_id": fields.String(description="UUID del recurso"),
    "available": fields.Boolean(description="true si el recurso está disponible en el instante consultado"),
    "reason": fields.String(description="outside_hours | holiday | absence | null"),
    "detail": fields.String(description="Detalle legible del motivo (nombre del festivo, rango de ausencia...)"),
})

_availability_list = ns.model("AvailabilityList", {
    "items": fields.List(fields.Nested(_availability_item)),
})


def _availability_to_dict(resource_id, availability) -> dict:
    return {
        "resource_id": str(resource_id),
        "available": availability.available,
        "reason": availability.reason,
        "detail": availability.detail,
    }


@ns.route("/resources/availability")
class ResourceAvailability(Resource):
    @ns.doc("get_resources_availability", params={
        "resource_ids": {"description": "UUIDs separados por coma (default: todos los recursos activos)", "type": "string"},
        "at": {"description": "Instante ISO-8601 a evaluar (default: ahora, UTC)", "type": "string"},
    })
    @ns.response(200, "Disponibilidad por recurso", _availability_list)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso tickets:assign", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "assign")
    def get(self):
        """Disponibilidad de recursos, consumida por el panel de asignación (FR-013 a FR-016).

        Solo lectura — reutiliza el permiso `tickets:assign` (research.md Decisión 7/8) y nunca
        modifica ni bloquea `POST /api/tickets/{id}/assign` (FR-015).
        """
        at_param = request.args.get("at")
        if at_param:
            try:
                now_utc = datetime.fromisoformat(at_param.replace("Z", "+00:00"))
                if now_utc.tzinfo is None:
                    now_utc = now_utc.replace(tzinfo=dt_timezone.utc)
            except ValueError:
                return {"error": "validation_error", "message": "El parámetro 'at' debe ser ISO-8601"}, 400
        else:
            now_utc = datetime.now(dt_timezone.utc)

        ids_param = request.args.get("resource_ids")
        try:
            db = get_db()
            resource_repo = ResourceRepository(db)
            if ids_param:
                ids = [parse_uuid(i) for i in ids_param.split(",") if i.strip()]
                if any(i is None for i in ids):
                    return {"error": "validation_error", "message": "resource_ids contiene un UUID inválido"}, 400
                resources = [r for r in (resource_repo.get_by_id(i) for i in ids) if r]
            else:
                resources, _total = resource_repo.list_paginated(page=1, page_size=1000, active=True)

            holiday_repo = HolidayRepository(db)
            schedule_repo = WorkScheduleRepository(db)
            absence_repo = AbsenceRequestRepository(db)
            # Aproximación: se usa la fecha UTC para buscar la ausencia vigente (las solicitudes
            # son por día completo, sin franja horaria — Assumptions de spec.md); el cálculo de
            # festivo/horario sí convierte a la hora local de cada recurso dentro del servicio.
            approx_date = now_utc.date()

            items = []
            for resource in resources:
                holidays = holiday_repo.list_by_country(resource.calendar_country) if resource.calendar_country else []
                slots = schedule_repo.list_by_resource(resource.id)
                active_absence = absence_repo.get_active_absence(resource.id, approx_date)
                availability = compute_availability(resource, now_utc, holidays, slots, active_absence)
                items.append(_availability_to_dict(resource.id, availability))
            return {"items": items}, 200
        except Exception:
            return server_error()


# ── Ausencias (Historia 2 — Jefe directo + RRHH, FR-008 a FR-012a) ─────────────────────────────

_absence_resource_ref = ns.model("AbsenceResourceRef", {
    "id": fields.String(description="UUID del recurso solicitante"),
    "full_name": fields.String(),
})

_absence_type_ref = ns.model("AbsenceTypeRef", {
    "id": fields.String(description="UUID del tipo de ausencia (catálogo)"),
    "name": fields.String(),
})

_absence_attachment_out = ns.model("AbsenceRequestAttachmentOut", {
    "id": fields.String(),
    "filename": fields.String(),
    "content_type": fields.String(),
    "size_bytes": fields.Integer(),
})

_absence_request_out = ns.model("AbsenceRequestOut", {
    "id": fields.String(),
    "resource": fields.Nested(_absence_resource_ref),
    "absence_type": fields.Nested(_absence_type_ref),
    "start_date": fields.String(description="YYYY-MM-DD"),
    "end_date": fields.String(description="YYYY-MM-DD"),
    "manager_status": fields.String(description="pending | approved | rejected"),
    "hr_status": fields.String(description="pending | approved | rejected"),
    "overall_status": fields.String(description="pending | approved | rejected (derivado)"),
    "notes": fields.String(),
    "attachments": fields.List(fields.Nested(_absence_attachment_out)),
    "created_at": fields.String(),
})

_absence_request_list = ns.model("AbsenceRequestList", {
    "items": fields.List(fields.Nested(_absence_request_out)),
})

_absence_request_input = ns.model("AbsenceRequestInput", {
    "absence_type_id": fields.String(required=True),
    "start_date": fields.String(required=True, description="YYYY-MM-DD"),
    "end_date": fields.String(required=True, description="YYYY-MM-DD"),
    "notes": fields.String(),
})

_absence_decision_input = ns.model("AbsenceDecisionInput", {
    "role": fields.String(required=True, description="manager | hr"),
    "decision": fields.String(required=True, description="approved | rejected"),
})


def _current_resource(db):
    """Recurso vinculado a la cuenta autenticada, o `None` si no tiene uno (ej. Usuario/cliente)."""
    return ResourceRepository(db).get_by_user_id(g.current_user.id)


def _parse_date(value) -> "date | None":
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _absence_request_to_dict(db, absence_request: AbsenceRequest) -> dict:
    resource = ResourceRepository(db).get_by_id(absence_request.resource_id)
    absence_type = CatalogRepository(db, "absence-types").get_by_id(absence_request.absence_type_id)
    attachments = AbsenceRequestRepository(db).list_attachments(absence_request.id)
    return {
        "id": str(absence_request.id),
        "resource": {"id": str(resource.id), "full_name": resource.full_name} if resource else None,
        "absence_type": absence_type,
        "start_date": absence_request.start_date.isoformat(),
        "end_date": absence_request.end_date.isoformat(),
        "manager_status": absence_request.manager_status,
        "hr_status": absence_request.hr_status,
        "overall_status": absence_service.overall_status(absence_request.manager_status, absence_request.hr_status),
        "notes": absence_request.notes,
        "attachments": [
            {"id": str(a.id), "filename": a.filename, "content_type": a.content_type, "size_bytes": a.size_bytes}
            for a in attachments
        ],
        "created_at": absence_request.created_at.isoformat(),
    }


def _can_view_request(db, current_resource, absence_request: AbsenceRequest) -> bool:
    """Dueño de la solicitud, su Jefe directo, o RRHH (`view_all`) — contracts/calendar-disponibilidad.md."""
    if current_resource and absence_request.resource_id == current_resource.id:
        return True
    if current_user_has("absence_requests", "view_all"):
        return True
    if current_resource:
        target = ResourceRepository(db).get_by_id(absence_request.resource_id)
        if target and target.manager_id == current_resource.id:
            return True
    return False


@ns.route("/absence-requests")
class AbsenceRequestList(Resource):
    @ns.doc("list_absence_requests", params={
        "scope": {"description": "own | manager | hr (default: own)", "type": "string"},
    })
    @ns.response(200, "Listado de solicitudes de ausencia", _absence_request_list)
    @ns.response(400, "scope inválido", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para el scope solicitado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self):
        """Listar solicitudes de ausencia según el scope (propias, de subordinados, o todas — RRHH)."""
        scope = request.args.get("scope", "own")
        if scope not in ("own", "manager", "hr"):
            return {"error": "validation_error", "message": "scope debe ser own, manager o hr"}, 400
        try:
            db = get_db()
            current_resource = _current_resource(db)
            repo = AbsenceRequestRepository(db)
            if scope == "own":
                items = repo.list_by_resource(current_resource.id) if current_resource else []
            elif scope == "manager":
                if not current_resource:
                    return _FORBIDDEN
                is_manager = (
                    db.query(ResourceModel.id).filter(ResourceModel.manager_id == current_resource.id).first()
                    is not None
                )
                if not is_manager:
                    return _FORBIDDEN
                items = repo.list_by_manager(current_resource.id)
            else:  # scope == "hr"
                if not current_user_has("absence_requests", "view_all"):
                    return _FORBIDDEN
                items = repo.list_all()
            return {"items": [_absence_request_to_dict(db, r) for r in items]}, 200
        except Exception:
            return server_error()

    @ns.doc("create_absence_request")
    @ns.expect(_absence_request_input)
    @ns.response(201, "Solicitud creada", _absence_request_out)
    @ns.response(400, "Datos inválidos, tipo inexistente o solapamiento de fechas", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso absence_requests:create", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("absence_requests", "create")
    def post(self):
        """Crear una solicitud de ausencia, con adjuntos opcionales (FR-008, FR-008a)."""
        is_multipart = bool(request.content_type and "multipart/form-data" in request.content_type)
        data = request.form.to_dict() if is_multipart else (request.get_json(silent=True) or {})
        files = request.files.getlist("files") if is_multipart else []

        absence_type_id = parse_uuid(data.get("absence_type_id"))
        start_date = _parse_date(data.get("start_date"))
        end_date = _parse_date(data.get("end_date"))
        if not absence_type_id or not start_date or not end_date:
            return {
                "error": "validation_error",
                "message": "absence_type_id, start_date y end_date son requeridos (fechas en formato YYYY-MM-DD)",
            }, 400
        try:
            db = get_db()
            current_resource = _current_resource(db)
            if not current_resource:
                return {
                    "error": "validation_error",
                    "message": "El usuario autenticado no tiene un Recurso vinculado",
                }, 400
            if not CatalogRepository(db, "absence-types").get_by_id(absence_type_id):
                return {"error": "validation_error", "message": "Tipo de ausencia inexistente"}, 400
            try:
                absence_service.validate_date_range(start_date, end_date)
            except absence_service.AbsenceServiceError as e:
                return {"error": e.code, "message": e.message}, 400
            repo = AbsenceRequestRepository(db)
            overlapping = repo.list_overlapping(current_resource.id, start_date, end_date)
            try:
                absence_service.assert_no_overlap(overlapping)
            except absence_service.AbsenceServiceError as e:
                return {"error": e.code, "message": e.message}, 400
            manager_status = absence_service.initial_manager_status(current_resource.manager_id is not None)
            new_request = AbsenceRequest.create(
                current_resource.id, absence_type_id, start_date, end_date,
                notes=(data.get("notes") or None), manager_status=manager_status,
            )
            created = repo.create(new_request)
            for f in files:
                if not f.filename:
                    continue
                content = f.read()
                path = attachment_storage.save(created.id, f.filename, content, entity_kind="absence_requests")
                repo.add_attachment(AbsenceRequestAttachment(
                    id=uuid.uuid4(), absence_request_id=created.id, filename=f.filename,
                    content_type=f.content_type or "application/octet-stream",
                    size_bytes=len(content), storage_path=path,
                ))
            return _absence_request_to_dict(db, created), 201
        except attachment_storage.AttachmentError as e:
            return {"error": "attachment_error", "message": e.message}, 400
        except Exception:
            return server_error()


@ns.route("/absence-requests/<string:request_id>/decision")
@ns.param("request_id", "UUID de la solicitud")
class AbsenceRequestDecision(Resource):
    @ns.doc("decide_absence_request")
    @ns.expect(_absence_decision_input)
    @ns.response(200, "Solicitud actualizada", _absence_request_out)
    @ns.response(400, "UUID o body inválido", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para decidir esta solicitud, o es propia (FR-012)", _error)
    @ns.response(404, "Solicitud no encontrada", _error)
    @ns.response(409, "Ese lado (manager/hr) ya fue decidido", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def patch(self, request_id: str):
        """Aprobar/rechazar como Jefe directo o RRHH (FR-010, FR-011, FR-011a, FR-012)."""
        rid = parse_uuid(request_id)
        if not rid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        body = request.get_json(silent=True) or {}
        role = body.get("role")
        decision = body.get("decision")
        if role not in ("manager", "hr") or decision not in ("approved", "rejected"):
            return {
                "error": "validation_error",
                "message": "role debe ser manager|hr y decision approved|rejected",
            }, 400
        try:
            db = get_db()
            repo = AbsenceRequestRepository(db)
            absence_request = repo.get_by_id(rid)
            if not absence_request:
                return {"error": "not_found", "message": "Solicitud no encontrada"}, 404
            current_resource = _current_resource(db)
            if not current_resource:
                return _FORBIDDEN
            try:
                absence_service.assert_not_own_request(current_resource.id, absence_request)
            except absence_service.AbsenceServiceError as e:
                return {"error": e.code, "message": e.message}, 403
            if role == "manager":
                target = ResourceRepository(db).get_by_id(absence_request.resource_id)
                if not target or target.manager_id != current_resource.id:
                    return _FORBIDDEN
            else:
                if not current_user_has("absence_requests", "decide_hr"):
                    return _FORBIDDEN
            try:
                absence_service.assert_can_decide(role, absence_request)
            except absence_service.AbsenceServiceError as e:
                return {"error": e.code, "message": e.message}, 409
            if role == "manager":
                updated = repo.update_decision(rid, manager_status=decision, manager_decided_by=g.current_user.id)
            else:
                updated = repo.update_decision(rid, hr_status=decision, hr_decided_by=g.current_user.id)
            return _absence_request_to_dict(db, updated), 200
        except Exception:
            return server_error()


@ns.route("/absence-requests/<string:request_id>/attachments")
@ns.param("request_id", "UUID de la solicitud")
class AbsenceRequestAttachments(Resource):
    @ns.doc("list_absence_request_attachments")
    @ns.response(200, "Adjuntos de la solicitud")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para ver esta solicitud", _error)
    @ns.response(404, "Solicitud no encontrada", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self, request_id: str):
        """Listar adjuntos de una solicitud de ausencia."""
        rid = parse_uuid(request_id)
        if not rid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        try:
            db = get_db()
            repo = AbsenceRequestRepository(db)
            absence_request = repo.get_by_id(rid)
            if not absence_request:
                return {"error": "not_found", "message": "Solicitud no encontrada"}, 404
            current_resource = _current_resource(db)
            if not _can_view_request(db, current_resource, absence_request):
                return _FORBIDDEN
            items = [
                {"id": str(a.id), "filename": a.filename, "content_type": a.content_type, "size_bytes": a.size_bytes}
                for a in repo.list_attachments(rid)
            ]
            return {"items": items}, 200
        except Exception:
            return server_error()

    @ns.doc("upload_absence_request_attachment")
    @ns.response(201, "Adjunto subido", _absence_attachment_out)
    @ns.response(400, "Archivo inválido o ausente", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para esta solicitud", _error)
    @ns.response(404, "Solicitud no encontrada", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def post(self, request_id: str):
        """Agregar un adjunto a una solicitud ya creada (FR-008a)."""
        rid = parse_uuid(request_id)
        if not rid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        file = request.files.get("file")
        if not file or not file.filename:
            return {"error": "validation_error", "message": "El campo 'file' es requerido"}, 400
        try:
            db = get_db()
            repo = AbsenceRequestRepository(db)
            absence_request = repo.get_by_id(rid)
            if not absence_request:
                return {"error": "not_found", "message": "Solicitud no encontrada"}, 404
            current_resource = _current_resource(db)
            if not _can_view_request(db, current_resource, absence_request):
                return _FORBIDDEN
            content = file.read()
            path = attachment_storage.save(rid, file.filename, content, entity_kind="absence_requests")
            attachment = AbsenceRequestAttachment(
                id=uuid.uuid4(), absence_request_id=rid, filename=file.filename,
                content_type=file.content_type or "application/octet-stream",
                size_bytes=len(content), storage_path=path,
            )
            created = repo.add_attachment(attachment)
            return {
                "id": str(created.id), "filename": created.filename,
                "content_type": created.content_type, "size_bytes": created.size_bytes,
            }, 201
        except attachment_storage.AttachmentError as e:
            return {"error": "attachment_error", "message": e.message}, 400
        except Exception:
            return server_error()


@ns.route("/absence-requests/<string:request_id>/attachments/<string:attachment_id>")
@ns.param("request_id", "UUID de la solicitud")
@ns.param("attachment_id", "UUID del adjunto")
class AbsenceRequestAttachmentDetail(Resource):
    @ns.doc("download_absence_request_attachment")
    @ns.produces(["application/octet-stream"])
    @ns.response(200, "Archivo (stream binario con el content-type original)")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso para esta solicitud", _error)
    @ns.response(404, "Adjunto no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self, request_id: str, attachment_id: str):
        """Descarga autenticada de un adjunto de la solicitud."""
        rid = parse_uuid(request_id)
        aid = parse_uuid(attachment_id)
        if not rid or not aid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        try:
            db = get_db()
            repo = AbsenceRequestRepository(db)
            absence_request = repo.get_by_id(rid)
            if not absence_request:
                return {"error": "not_found", "message": "Solicitud no encontrada"}, 404
            current_resource = _current_resource(db)
            if not _can_view_request(db, current_resource, absence_request):
                return _FORBIDDEN
            attachment = repo.get_attachment(rid, aid)
            if not attachment:
                return {"error": "not_found", "message": "Adjunto no encontrado"}, 404
            path = attachment_storage.open_path(attachment.storage_path)
            return send_file(path, mimetype=attachment.content_type,
                             as_attachment=True, download_name=attachment.filename)
        except attachment_storage.AttachmentError as e:
            return {"error": "attachment_error", "message": e.message}, 404
        except Exception:
            return server_error()

    @ns.doc("delete_absence_request_attachment")
    @ns.response(204, "Adjunto eliminado")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para esta solicitud", _error)
    @ns.response(404, "Solicitud o adjunto no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def delete(self, request_id: str, attachment_id: str):
        """Eliminar un adjunto de la solicitud."""
        rid = parse_uuid(request_id)
        aid = parse_uuid(attachment_id)
        if not rid or not aid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        try:
            db = get_db()
            repo = AbsenceRequestRepository(db)
            absence_request = repo.get_by_id(rid)
            if not absence_request:
                return {"error": "not_found", "message": "Solicitud no encontrada"}, 404
            current_resource = _current_resource(db)
            if not _can_view_request(db, current_resource, absence_request):
                return _FORBIDDEN
            if not repo.delete_attachment(rid, aid):
                return {"error": "not_found", "message": "Adjunto no encontrado"}, 404
            return "", 204
        except Exception:
            return server_error()


# ── Festivos (Historia 3 — calendario con festivos por país, FR-001/002/004/005) ───────────────

_holiday_out = ns.model("HolidayOut", {
    "id": fields.String(),
    "country": fields.String(description="ISO 3166-1 alpha-2"),
    "holiday_date": fields.String(description="YYYY-MM-DD"),
    "name": fields.String(),
    "active": fields.Boolean(),
    "category": fields.String(description="oficial | regional_religioso"),
    "source": fields.String(description="api | manual"),
})

_holiday_list = ns.model("HolidayList", {"items": fields.List(fields.Nested(_holiday_out))})

_holiday_input = ns.model("HolidayInput", {
    "country": fields.String(required=True, description="ISO 3166-1 alpha-2"),
    "holiday_date": fields.String(required=True, description="YYYY-MM-DD"),
    "name": fields.String(required=True),
    "category": fields.String(description="oficial | regional_religioso (default oficial)"),
})

_holiday_update_input = ns.model("HolidayUpdateInput", {
    "name": fields.String(),
    "holiday_date": fields.String(description="YYYY-MM-DD"),
    "category": fields.String(description="oficial | regional_religioso"),
})

_HOLIDAY_CATEGORIES = ("oficial", "regional_religioso")


def _holiday_to_dict(holiday) -> dict:
    return {
        "id": str(holiday.id), "country": holiday.country,
        "holiday_date": holiday.holiday_date.isoformat(), "name": holiday.name,
        "active": holiday.active, "category": holiday.category, "source": holiday.source,
    }


@ns.route("/holidays")
class HolidayList(Resource):
    @ns.doc("list_holidays", params={"country": {"description": "ISO 3166-1 alpha-2", "type": "string"}})
    @ns.response(200, "Festivos del país (activos)", _holiday_list)
    @ns.response(400, "Falta el parámetro country", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self):
        """Listar festivos activos de un país — lectura abierta a cualquier autenticado (US1/US3).

        Si el país aún no tiene ningún registro de sincronización (`holiday_sync_status`), intenta
        una sincronización síncrona única contra la fuente externa antes de responder (spec 021,
        FR-001/FR-004). Un fallo de esa sincronización nunca produce error HTTP — se responde con
        lo que ya exista en base (FR-003)."""
        country = request.args.get("country")
        if not country:
            return {"error": "validation_error", "message": "El parámetro 'country' es requerido"}, 400
        try:
            db = get_db()
            year = datetime.now(dt_timezone.utc).year
            if HolidaySyncStatusRepository(db).get(country, year) is None:
                sync_country(db, country, year)
                sync_country(db, country, year + 1)
            items = [_holiday_to_dict(h) for h in HolidayRepository(db).list_by_country(country)]
            return {"items": items}, 200
        except Exception:
            return server_error()

    @ns.doc("create_holiday")
    @ns.expect(_holiday_input)
    @ns.response(201, "Festivo creado", _holiday_out)
    @ns.response(400, "Datos inválidos o festivo duplicado", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso holidays:manage", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("holidays", "manage")
    def post(self):
        """Crear un festivo (mantenimiento del catálogo, Admin/RRHH)."""
        body = request.get_json(silent=True) or {}
        country = body.get("country")
        name = body.get("name")
        holiday_date = _parse_date(body.get("holiday_date"))
        category = body.get("category", "oficial")
        if not country or not name or not holiday_date:
            return {
                "error": "validation_error",
                "message": "country, holiday_date (YYYY-MM-DD) y name son requeridos",
            }, 400
        if category not in _HOLIDAY_CATEGORIES:
            return {"error": "validation_error", "message": "category debe ser oficial o regional_religioso"}, 400
        try:
            db = get_db()
            repo = HolidayRepository(db)
            if repo.exists(country, holiday_date, name):
                return {"error": "validation_error", "message": "Ese festivo ya existe para ese país y fecha"}, 400
            created = repo.create(Holiday.create(country, holiday_date, name, category=category))
            return _holiday_to_dict(created), 201
        except Exception:
            return server_error()


@ns.route("/holidays/<string:holiday_id>")
@ns.param("holiday_id", "UUID del festivo")
class HolidayDetail(Resource):
    @ns.doc("update_holiday")
    @ns.expect(_holiday_update_input)
    @ns.response(200, "Festivo actualizado", _holiday_out)
    @ns.response(400, "UUID o datos inválidos", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso holidays:manage", _error)
    @ns.response(404, "Festivo no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("holidays", "manage")
    def patch(self, holiday_id: str):
        """Editar nombre/fecha/categoría de un festivo existente (spec 021, FR-009). Cualquier
        edición fija `source='manual'` — la sincronización automática nunca vuelve a sobrescribir
        esta fila."""
        hid = parse_uuid(holiday_id)
        if not hid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        body = request.get_json(silent=True) or {}
        category = body.get("category")
        if category is not None and category not in _HOLIDAY_CATEGORIES:
            return {"error": "validation_error", "message": "category debe ser oficial o regional_religioso"}, 400
        holiday_date = _parse_date(body.get("holiday_date")) if "holiday_date" in body else None
        if "holiday_date" in body and holiday_date is None:
            return {"error": "validation_error", "message": "holiday_date debe ser YYYY-MM-DD"}, 400
        try:
            db = get_db()
            updated = HolidayRepository(db).update(
                hid, name=body.get("name"), holiday_date=holiday_date, category=category)
            if not updated:
                return {"error": "not_found", "message": "Festivo no encontrado"}, 404
            return _holiday_to_dict(updated), 200
        except Exception:
            return server_error()


@ns.route("/holidays/<string:holiday_id>/<string:action>")
@ns.param("holiday_id", "UUID del festivo")
@ns.param("action", "activate | deactivate")
class HolidayToggle(Resource):
    @ns.doc("toggle_holiday")
    @ns.response(200, "Festivo actualizado", _holiday_out)
    @ns.response(400, "UUID o acción inválida", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso holidays:manage", _error)
    @ns.response(404, "Festivo no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("holidays", "manage")
    def patch(self, holiday_id: str, action: str):
        """Activar/desactivar un festivo sin borrar histórico."""
        hid = parse_uuid(holiday_id)
        if not hid or action not in ("activate", "deactivate"):
            return {"error": "validation_error", "message": "ID o acción inválida"}, 400
        try:
            db = get_db()
            updated = HolidayRepository(db).set_active(hid, action == "activate")
            if not updated:
                return {"error": "not_found", "message": "Festivo no encontrado"}, 404
            return _holiday_to_dict(updated), 200
        except Exception:
            return server_error()


# ── Horario laboral (Historia 4 — franjas semanales por recurso, FR-006) ───────────────────────

_work_schedule_slot = ns.model("WorkScheduleSlotIO", {
    "weekday": fields.Integer(description="0=lunes ... 6=domingo"),
    "start_time": fields.String(description="HH:MM, hora local del recurso"),
    "end_time": fields.String(description="HH:MM, debe ser mayor que start_time"),
})

_work_schedule_out = ns.model("WorkScheduleOut", {
    "items": fields.List(fields.Nested(_work_schedule_slot)),
    "is_default": fields.Boolean(description="true si el recurso no tiene franjas propias (se muestra el default)"),
})

_work_schedule_input = ns.model("WorkScheduleInput", {
    "items": fields.List(fields.Nested(_work_schedule_slot), required=True),
})


def _parse_time(value) -> "time | None":
    try:
        h, m = str(value).split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError, TypeError):
        return None


def _work_schedule_to_dict(slots: list[WorkScheduleSlot]) -> dict:
    if not slots:
        return {
            "items": [
                {"weekday": wd, "start_time": DEFAULT_START_TIME.strftime("%H:%M"),
                 "end_time": DEFAULT_END_TIME.strftime("%H:%M")}
                for wd in DEFAULT_WEEKDAYS
            ],
            "is_default": True,
        }
    return {
        "items": [
            {"weekday": s.weekday, "start_time": s.start_time.strftime("%H:%M"),
             "end_time": s.end_time.strftime("%H:%M")}
            for s in sorted(slots, key=lambda s: s.weekday)
        ],
        "is_default": False,
    }


@ns.route("/resources/<string:resource_id>/work-schedule")
@ns.param("resource_id", "UUID del recurso")
class ResourceWorkSchedule(Resource):
    @ns.doc("get_resource_work_schedule")
    @ns.response(200, "Horario laboral del recurso (default si no tiene franjas propias)", _work_schedule_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para ver este recurso", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, resource_id: str):
        """Franjas semanales del recurso; `is_default=true` cuando no tiene filas propias (FR-006)."""
        rid = parse_uuid(resource_id)
        if not rid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        try:
            db = get_db()
            if not ResourceRepository(db).get_by_id(rid):
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            slots = WorkScheduleRepository(db).list_by_resource(rid)
            return _work_schedule_to_dict(slots), 200
        except Exception:
            return server_error()

    @ns.doc("set_resource_work_schedule")
    @ns.expect(_work_schedule_input)
    @ns.response(200, "Horario laboral reemplazado", _work_schedule_out)
    @ns.response(400, "Datos inválidos (weekday fuera de 0-6, end_time<=start_time, o repetido)", _error)
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin permiso para editar este recurso", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def put(self, resource_id: str):
        """Reemplaza por completo las franjas semanales del recurso (`PUT` idempotente, FR-006)."""
        rid = parse_uuid(resource_id)
        if not rid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        body = request.get_json(silent=True) or {}
        items = body.get("items")
        if not isinstance(items, list):
            return {"error": "validation_error", "message": "'items' debe ser una lista"}, 400
        slots = []
        seen_weekdays = set()
        for item in items:
            weekday = item.get("weekday") if isinstance(item, dict) else None
            start_time = _parse_time(item.get("start_time")) if isinstance(item, dict) else None
            end_time = _parse_time(item.get("end_time")) if isinstance(item, dict) else None
            if not isinstance(weekday, int) or weekday < 0 or weekday > 6:
                return {"error": "validation_error", "message": "weekday debe ser un entero entre 0 y 6"}, 400
            if weekday in seen_weekdays:
                return {"error": "validation_error", "message": f"weekday {weekday} repetido"}, 400
            if not start_time or not end_time or end_time <= start_time:
                return {
                    "error": "validation_error",
                    "message": "start_time/end_time inválidos (formato HH:MM, end_time debe ser mayor)",
                }, 400
            seen_weekdays.add(weekday)
            slots.append(WorkScheduleSlot.create(rid, weekday, start_time, end_time))
        try:
            db = get_db()
            if not ResourceRepository(db).get_by_id(rid):
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            updated = WorkScheduleRepository(db).replace_for_resource(rid, slots)
            return _work_schedule_to_dict(updated), 200
        except Exception:
            return server_error()


ResourceWorkSchedule.method_decorators = [enforce_module("resources", allow_own_resource_edit=True)]
