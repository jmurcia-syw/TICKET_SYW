from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.database import get_db
from backend.domain.entities.project import Project
from backend.domain.services.project_service import ProjectService, ProjectBusinessError
from backend.api.routes._shared import parse_uuid, error_model, server_error
from datetime import date

ns = Namespace("projects", description="Gestión de proyectos", path="/api/projects")
_svc = ProjectService()

# ── Models ────────────────────────────────────────────────────────────────────

_error = error_model(ns, "ProjectError")

_project_out = ns.model("Project", {
    "id": fields.String(description="UUID del proyecto"),
    "client_id": fields.String(description="UUID del cliente propietario"),
    "client_name": fields.String(description="Nombre del cliente (join)"),
    "name": fields.String(description="Nombre del proyecto"),
    "description": fields.String(description="Descripción"),
    "overview": fields.String(description="Overview / resumen ejecutivo (SDD V3)"),
    "sale_services_usd": fields.Float(description="Valor de venta de servicios en USD"),
    "sale_licenses_usd": fields.Float(description="Valor de venta de licencias en USD"),
    "sale_subscriptions_usd": fields.Float(description="Valor de venta de suscripciones en USD"),
    "components_sold": fields.String(description="Componentes vendidos"),
    "active": fields.Boolean(description="Estado activo"),
    "start_date": fields.String(description="Fecha de inicio (YYYY-MM-DD)"),
    "end_date_estimated": fields.String(description="Fecha estimada de fin (YYYY-MM-DD)"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_project_list_out = ns.model("ProjectList", {
    "items": fields.List(fields.Nested(_project_out)),
    "total": fields.Integer(description="Total de registros"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_project_input = ns.model("ProjectInput", {
    "client_id": fields.String(required=True, description="UUID del cliente", example="00000000-0000-0000-0000-000000000001"),
    "name": fields.String(required=True, description="Nombre del proyecto", example="Implementación JDE GL"),
    "description": fields.String(description="Descripción del proyecto"),
    "overview": fields.String(description="Overview / resumen ejecutivo"),
    "sale_services_usd": fields.Float(description="Valor de venta de servicios en USD"),
    "sale_licenses_usd": fields.Float(description="Valor de venta de licencias en USD"),
    "sale_subscriptions_usd": fields.Float(description="Valor de venta de suscripciones en USD"),
    "components_sold": fields.String(description="Componentes vendidos"),
    "start_date": fields.String(required=True, description="Fecha de inicio (YYYY-MM-DD)", example="2026-01-15"),
    "end_date_estimated": fields.String(description="Fecha estimada de fin (YYYY-MM-DD)", example="2026-06-30"),
})

_project_update = ns.model("ProjectUpdate", {
    "name": fields.String(description="Nuevo nombre"),
    "description": fields.String(description="Nueva descripción"),
    "overview": fields.String(description="Overview / resumen ejecutivo"),
    "sale_services_usd": fields.Float(description="Valor de venta de servicios en USD"),
    "sale_licenses_usd": fields.Float(description="Valor de venta de licencias en USD"),
    "sale_subscriptions_usd": fields.Float(description="Valor de venta de suscripciones en USD"),
    "components_sold": fields.String(description="Componentes vendidos"),
    "start_date": fields.String(description="Fecha de inicio (YYYY-MM-DD)"),
    "end_date_estimated": fields.String(description="Fecha estimada de fin (YYYY-MM-DD), null para eliminar"),
})

_status_result = ns.model("ProjectStatusResult", {
    "id": fields.String(description="UUID del proyecto"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})


_SALE_FIELDS = ("sale_services_usd", "sale_licenses_usd", "sale_subscriptions_usd")


def _parse_sale_amounts(data: dict) -> tuple[dict, str | None]:
    """Extrae y valida los montos de venta (>= 0). Devuelve (valores, error)."""
    amounts: dict = {}
    for f in _SALE_FIELDS:
        if f in data:
            if data[f] is None:
                amounts[f] = None
                continue
            try:
                value = float(data[f])
            except (TypeError, ValueError):
                return {}, f"El campo {f} debe ser numérico"
            if value < 0:
                return {}, f"El campo {f} no puede ser negativo"
            amounts[f] = value
    return amounts, None


def _project_to_dict(project, client_name=None) -> dict:
    d = {
        "id": str(project.id),
        "client_id": str(project.client_id),
        "name": project.name,
        "description": project.description,
        "overview": project.overview,
        "sale_services_usd": project.sale_services_usd,
        "sale_licenses_usd": project.sale_licenses_usd,
        "sale_subscriptions_usd": project.sale_subscriptions_usd,
        "components_sold": project.components_sold,
        "active": project.active,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date_estimated": project.end_date_estimated.isoformat() if project.end_date_estimated else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }
    if client_name is not None:
        d["client_name"] = client_name
    return d


# ── Resources ────────────────────────────────────────────────────────────────

@ns.route("")
class ProjectList(Resource):
    @ns.doc(
        "list_projects",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "client_id": {"description": "Filtrar por UUID de cliente", "type": "string"},
            "search": {"description": "Búsqueda por nombre", "type": "string"},
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Listado de proyectos", _project_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar proyectos con paginación y filtros. Incluye nombre del cliente."""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        client_id_str = request.args.get("client_id")
        search = request.args.get("search", "").strip() or None
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        client_id = parse_uuid(client_id_str) if client_id_str else None
        try:
            db = get_db()
            repo = ProjectRepository(db)
            client_repo = ClientRepository(db)
            items, total = repo.list_paginated(page=page, page_size=page_size, client_id=client_id, search=search, active=active)
            results = []
            for p in items:
                c = client_repo.get_by_id(p.client_id)
                results.append(_project_to_dict(p, client_name=c.name if c else None))
            return {"items": results, "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_project")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_project_input, validate=False)
    @ns.response(201, "Proyecto creado", _project_out)
    @ns.response(400, "Datos inválidos, fechas mal formateadas, fecha de fin anterior a inicio o fecha de inicio en un mes anterior al actual", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(409, "Conflicto de negocio (cliente inactivo, nombre duplicado)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un nuevo proyecto. Requiere client_id, name y start_date (YYYY-MM-DD)."""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        for field in ("client_id", "name", "start_date"):
            if not data.get(field):
                return {"error": "validation_error", "message": f"El campo {field} es requerido"}, 400
        client_id = parse_uuid(data["client_id"])
        if not client_id:
            return {"error": "validation_error", "message": "client_id invalido"}, 400
        try:
            start_date = date.fromisoformat(data["start_date"])
        except ValueError:
            return {"error": "validation_error", "message": "start_date debe ser YYYY-MM-DD"}, 400
        end_date = None
        if data.get("end_date_estimated"):
            try:
                end_date = date.fromisoformat(data["end_date_estimated"])
            except ValueError:
                return {"error": "validation_error", "message": "end_date_estimated debe ser YYYY-MM-DD"}, 400
        amounts, amount_error = _parse_sale_amounts(data)
        if amount_error:
            return {"error": "validation_error", "message": amount_error}, 400
        try:
            db = get_db()
            _svc.validate_create(
                client_id=client_id, name=data["name"], start_date=start_date, end_date=end_date,
                clients_repo=ClientRepository(db), projects_repo=ProjectRepository(db),
            )
            project = Project.create(
                client_id=client_id, name=data["name"], start_date=start_date,
                description=data.get("description"), end_date_estimated=end_date,
                overview=data.get("overview"), components_sold=data.get("components_sold"),
                **amounts,
            )
            created = ProjectRepository(db).create(project)
            return _project_to_dict(created), 201, {"Location": f"/api/projects/{created.id}"}
        except ProjectBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:project_id>")
@ns.param("project_id", "UUID del proyecto")
class ProjectDetail(Resource):
    @ns.doc("get_project")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Detalle del proyecto", _project_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Proyecto no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, project_id: str):
        """Obtener detalle de un proyecto"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        try:
            db = get_db()
            project = ProjectRepository(db).get_by_id(uid)
            if not project:
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            c = ClientRepository(db).get_by_id(project.client_id)
            return _project_to_dict(project, client_name=c.name if c else None), 200
        except Exception:
            return server_error()

    @ns.doc("update_project")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_project_update, validate=False)
    @ns.response(200, "Proyecto actualizado", _project_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Proyecto no encontrado", _error)
    @ns.response(409, "Conflicto de negocio (nombre duplicado)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, project_id: str):
        """Actualizar campos de un proyecto (PATCH parcial)"""
        from flask import request
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = get_db()
            repo = ProjectRepository(db)
            project = repo.get_by_id(uid)
            if not project:
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            amounts, amount_error = _parse_sale_amounts(data)
            if amount_error:
                return {"error": "validation_error", "message": amount_error}, 400
            if "name" in data:
                new_name = str(data["name"]).strip()
                if not new_name:
                    return {"error": "validation_error", "message": "El nombre no puede estar vacio"}, 400
                _svc.validate_name(new_name)
                if new_name != project.name:
                    existing = ProjectRepository(db).get_by_client_and_name(project.client_id, new_name)
                    if existing and existing.id != project.id:
                        raise ProjectBusinessError(
                            "name_duplicate", "Ya existe un proyecto con ese nombre para este cliente")
                data["name"] = new_name
            for field in ("name", "description", "overview", "components_sold"):
                if field in data:
                    setattr(project, field, data[field])
            for field, value in amounts.items():
                setattr(project, field, value)
            if "start_date" in data:
                project.start_date = date.fromisoformat(data["start_date"])
            if "end_date_estimated" in data:
                project.end_date_estimated = date.fromisoformat(data["end_date_estimated"]) if data["end_date_estimated"] else None
            if "start_date" in data or "end_date_estimated" in data:
                _svc.validate_dates(project.start_date, project.end_date_estimated)
            updated = repo.update(project)
            return _project_to_dict(updated), 200
        except ProjectBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except ValueError as exc:
            return {"error": "validation_error", "message": str(exc)}, 400
        except Exception:
            return server_error()


@ns.route("/<string:project_id>/deactivate")
@ns.param("project_id", "UUID del proyecto")
class ProjectDeactivate(Resource):
    @ns.doc("deactivate_project")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Proyecto desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Proyecto no encontrado", _error)
    @ns.response(409, "El proyecto ya está inactivo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, project_id: str):
        """Desactivar un proyecto"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        try:
            db = get_db()
            repo = ProjectRepository(db)
            project = repo.get_by_id(uid)
            if not project:
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            if not project.active:
                return {"error": "already_inactive", "message": "El proyecto ya esta inactivo"}, 409
            repo.deactivate(uid)
            return {"id": project_id, "active": False}, 200
        except Exception:
            return server_error()


@ns.route("/<string:project_id>/activate")
@ns.param("project_id", "UUID del proyecto")
class ProjectActivate(Resource):
    @ns.doc("activate_project")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Proyecto activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Proyecto no encontrado", _error)
    @ns.response(409, "El proyecto ya está activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, project_id: str):
        """Activar un proyecto previamente desactivado"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        try:
            db = get_db()
            repo = ProjectRepository(db)
            project = repo.get_by_id(uid)
            if not project:
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            if project.active:
                return {"error": "already_active", "message": "El proyecto ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": project_id, "active": True}, 200
        except Exception:
            return server_error()


# ── Enforcement FR-022 (spec 002): JWT + permiso por módulo/acción ─────────────
from backend.api.middleware.rbac import enforce_module as _enforce

for _cls in (ProjectList, ProjectDetail, ProjectDeactivate, ProjectActivate):
    _cls.method_decorators = [_enforce("projects")]
