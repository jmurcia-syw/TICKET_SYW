from flask import request
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.infra.database import get_db
from backend.infra.models.catalog_model import CATALOG_MODELS, CATALOG_TICKET_COLUMN
from backend.infra.repositories.catalog_repo import CatalogRepository
from backend.infra.repositories.ticket_repo import TicketRepository

ns = Namespace("catalogs", description="Catálogos de tickets (herramienta, proceso, tipo de resolución)",
               path="/api/catalogs")

_error = error_model(ns, "CatalogError")

_catalog_out = ns.model("CatalogItem", {
    "id": fields.String(description="UUID"),
    "name": fields.String(description="Nombre único"),
    "active": fields.Boolean(description="Estado activo"),
})

_catalog_input = ns.model("CatalogInput", {
    "name": fields.String(required=True, description="Nombre del valor", example="JDE"),
})


def _validate_catalog(catalog: str):
    if catalog not in CATALOG_MODELS:
        return {"error": "not_found", "message": "Catálogo desconocido"}, 404
    return None


@ns.route("/<string:catalog>")
@ns.param("catalog", "tools | processes | resolution-types")
class CatalogList(Resource):
    @ns.doc("list_catalog", params={"active": {"description": "true/false/all (default true)", "type": "string"}})
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Valores del catálogo", [_catalog_out])
    @ns.response(404, "Catálogo desconocido", _error)
    @require_permission("catalogs", "view")
    def get(self, catalog: str):
        """Listar valores de un catálogo"""
        invalid = _validate_catalog(catalog)
        if invalid:
            return invalid
        active_param = request.args.get("active", "true")
        active = None if active_param == "all" else active_param.lower() == "true"
        try:
            items = CatalogRepository(get_db(), catalog).list_all(active=active)
            return {"items": items, "total": len(items)}, 200
        except Exception:
            return server_error()

    @ns.doc("create_catalog_value")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_catalog_input, validate=False)
    @ns.response(201, "Valor creado", _catalog_out)
    @ns.response(409, "Nombre duplicado", _error)
    @require_permission("catalogs", "create")
    def post(self, catalog: str):
        """Agregar un valor al catálogo"""
        invalid = _validate_catalog(catalog)
        if invalid:
            return invalid
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        if not name:
            return {"error": "validation_error", "message": "El campo 'name' es requerido"}, 400
        try:
            repo = CatalogRepository(get_db(), catalog)
            if repo.get_by_name(name):
                return {"error": "name_duplicate", "message": f"Ya existe el valor '{name}' en el catálogo"}, 409
            return repo.create(name), 201
        except Exception:
            return server_error()


@ns.route("/<string:catalog>/<string:item_id>/deactivate")
@ns.param("catalog", "tools | processes | resolution-types")
class CatalogDeactivate(Resource):
    @ns.doc("deactivate_catalog_value")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Valor desactivado", _catalog_out)
    @ns.response(409, "Valor en uso por tickets abiertos", _error)
    @require_permission("catalogs", "deactivate")
    def patch(self, catalog: str, item_id: str):
        """Desactivar un valor (bloqueado si tickets no finales lo usan)"""
        invalid = _validate_catalog(catalog)
        if invalid:
            return invalid
        uid = parse_uuid(item_id)
        if not uid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        try:
            db = get_db()
            in_use = TicketRepository(db).count_using_catalog(CATALOG_TICKET_COLUMN[catalog], uid)
            if in_use > 0:
                return {"error": "in_use",
                        "message": f"No se puede desactivar: {in_use} ticket(s) abierto(s) usan este valor",
                        "open_tickets_count": in_use}, 409
            result = CatalogRepository(db, catalog).set_active(uid, False)
            if not result:
                return {"error": "not_found", "message": "Valor no encontrado"}, 404
            return result, 200
        except Exception:
            return server_error()


@ns.route("/<string:catalog>/<string:item_id>/activate")
@ns.param("catalog", "tools | processes | resolution-types")
class CatalogActivate(Resource):
    @ns.doc("activate_catalog_value")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Valor activado", _catalog_out)
    @require_permission("catalogs", "deactivate")
    def patch(self, catalog: str, item_id: str):
        """Reactivar un valor del catálogo"""
        invalid = _validate_catalog(catalog)
        if invalid:
            return invalid
        uid = parse_uuid(item_id)
        if not uid:
            return {"error": "validation_error", "message": "ID inválido"}, 400
        try:
            result = CatalogRepository(get_db(), catalog).set_active(uid, True)
            if not result:
                return {"error": "not_found", "message": "Valor no encontrado"}, 404
            return result, 200
        except Exception:
            return server_error()
