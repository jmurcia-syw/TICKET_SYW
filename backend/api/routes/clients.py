from flask import g
from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.database import get_db
from backend.domain.entities.client import Client, ClientSystem
from backend.domain.services.client_service import ClientService, ClientBusinessError
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("clients", description="Gestión de clientes", path="/api/clients")
_svc = ClientService()

# ── Models ────────────────────────────────────────────────────────────────────

_error = error_model(ns, "ClientError")

_client_out = ns.model("Client", {
    "id": fields.String(description="UUID del cliente"),
    "name": fields.String(description="Nombre del cliente"),
    "slug": fields.String(description="Slug URL-safe"),
    "active": fields.Boolean(description="Estado activo"),
    "contact_name": fields.String(description="Nombre del contacto"),
    "contact_email": fields.String(description="Email del contacto"),
    "contact_phone": fields.String(description="Teléfono del contacto"),
    "annual_billing_usd": fields.Float(description="Facturación anual del cliente en USD (SDD V3)"),
    "notes": fields.String(description="Notas internas"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
    "updated_at": fields.String(description="Fecha de última actualización ISO-8601"),
})

_client_detail_out = ns.inherit("ClientDetail", _client_out, {
    "vpn_ips": fields.String(description="IPs de VPN (dato sensible)"),
    "vpn_credentials": fields.String(description="Credenciales VPN (dato sensible)"),
})

_client_list_out = ns.model("ClientList", {
    "items": fields.List(fields.Nested(_client_out)),
    "total": fields.Integer(description="Total de registros"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_client_input = ns.model("ClientInput", {
    "name": fields.String(required=True, description="Nombre del cliente", example="Acme Corp"),
    "contact_name": fields.String(description="Nombre del contacto", example="Juan García"),
    "contact_email": fields.String(description="Email del contacto", example="juan@acme.com"),
    "contact_phone": fields.String(description="Teléfono", example="+57 300 000 0000"),
    "vpn_ips": fields.String(description="IPs de VPN (cifradas en reposo)"),
    "vpn_credentials": fields.String(description="Credenciales VPN (cifradas en reposo)"),
    "annual_billing_usd": fields.Float(description="Facturación anual en USD"),
    "notes": fields.String(description="Notas internas"),
})

_client_update = ns.model("ClientUpdate", {
    "name": fields.String(description="Nuevo nombre"),
    "contact_name": fields.String(description="Nombre del contacto"),
    "contact_email": fields.String(description="Email del contacto"),
    "contact_phone": fields.String(description="Teléfono"),
    "vpn_ips": fields.String(description="IPs de VPN"),
    "vpn_credentials": fields.String(description="Credenciales VPN"),
    "annual_billing_usd": fields.Float(description="Facturación anual en USD"),
    "notes": fields.String(description="Notas internas"),
})

_system_out = ns.model("ClientSystem", {
    "id": fields.String(description="UUID del sistema"),
    "client_id": fields.String(description="UUID del cliente"),
    "system_type": fields.String(description="Tipo: ERP, WMS, CRM, OTM, otro"),
    "brand": fields.String(description="Marca (JD Edwards, Oracle Fusion, SAP...)"),
    "version": fields.String(description="Versión"),
    "notes": fields.String(description="Notas"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_system_list_out = ns.model("ClientSystemList", {
    "items": fields.List(fields.Nested(_system_out)),
    "total": fields.Integer(description="Total de sistemas"),
})

_system_input = ns.model("ClientSystemInput", {
    "system_type": fields.String(required=True, description="Tipo de sistema", example="ERP"),
    "brand": fields.String(required=True, description="Marca", example="JD Edwards"),
    "version": fields.String(description="Versión", example="9.2"),
    "notes": fields.String(description="Notas"),
})

_status_result = ns.model("StatusResult", {
    "id": fields.String(description="UUID del cliente"),
    "active": fields.Boolean(description="Nuevo estado activo"),
    "warning": fields.String(description="Aviso si había proyectos activos"),
    "active_projects_count": fields.Integer(description="Proyectos activos afectados"),
})


def _client_to_dict(client, include_sensitive: bool = False) -> dict:
    d = {
        "id": str(client.id),
        "name": client.name,
        "slug": client.slug,
        "active": client.active,
        "contact_name": client.contact_name,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
        "annual_billing_usd": client.annual_billing_usd,
        "notes": client.notes,
        "created_at": client.created_at.isoformat() if client.created_at else None,
        "updated_at": client.updated_at.isoformat() if client.updated_at else None,
    }
    if include_sensitive:
        d["vpn_ips"] = client.vpn_ips
        d["vpn_credentials"] = client.vpn_credentials
    return d


def _parse_billing(data: dict) -> tuple[dict, str | None]:
    if "annual_billing_usd" not in data:
        return {}, None
    if data["annual_billing_usd"] is None:
        return {"annual_billing_usd": None}, None
    try:
        value = float(data["annual_billing_usd"])
    except (TypeError, ValueError):
        return {}, "El campo annual_billing_usd debe ser numérico"
    if value < 0:
        return {}, "El campo annual_billing_usd no puede ser negativo"
    return {"annual_billing_usd": value}, None


def _system_to_dict(system) -> dict:
    return {
        "id": str(system.id),
        "client_id": str(system.client_id),
        "system_type": system.system_type,
        "brand": system.brand,
        "version": system.version,
        "notes": system.notes,
        "created_at": system.created_at.isoformat() if system.created_at else None,
    }


# ── Resources ────────────────────────────────────────────────────────────────

@ns.route("")
class ClientList(Resource):
    @ns.doc(
        "list_clients",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "search": {"description": "Búsqueda por nombre o slug", "type": "string"},
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Listado de clientes", _client_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar clientes con paginación y filtros"""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        search = request.args.get("search", "").strip() or None
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        try:
            db = get_db()
            items, total = ClientRepository(db).list_paginated(page=page, page_size=page_size, search=search, active=active)
            return {"items": [_client_to_dict(c) for c in items], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_client")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_client_input, validate=False)
    @ns.response(201, "Cliente creado", _client_detail_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(409, "Conflicto de negocio (nombre duplicado)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un nuevo cliente"""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        name = data.get("name", "").strip()
        if not name:
            return {"error": "validation_error", "message": "El campo 'name' es requerido"}, 400
        billing, billing_error = _parse_billing(data)
        if billing_error:
            return {"error": "validation_error", "message": billing_error}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            _svc.validate_unique_name(name, repo=repo)
            client = Client.create(
                name=name,
                contact_name=data.get("contact_name"),
                contact_email=data.get("contact_email"),
                contact_phone=data.get("contact_phone"),
                vpn_ips=data.get("vpn_ips"),
                vpn_credentials=data.get("vpn_credentials"),
                notes=data.get("notes"),
                **billing,
            )
            created = repo.create(client)
            return _client_to_dict(created, include_sensitive=True), 201, {"Location": f"/api/clients/{created.id}"}
        except ClientBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:client_id>")
@ns.param("client_id", "UUID del cliente")
class ClientDetail(Resource):
    @ns.doc("get_client")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Detalle del cliente (incluye campos VPN sensibles)", _client_detail_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, client_id: str):
        """Obtener detalle de un cliente (incluye campos VPN sensibles)"""
        uid = parse_uuid(client_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de cliente invalido"}, 400
        try:
            db = get_db()
            client = ClientRepository(db).get_by_id(uid, include_sensitive=True)
            if not client:
                return {"error": "not_found", "message": "Cliente no encontrado"}, 404
            return _client_to_dict(client, include_sensitive=True), 200
        except Exception:
            return server_error()

    @ns.doc("update_client")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_client_update, validate=False)
    @ns.response(200, "Cliente actualizado", _client_detail_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(409, "Conflicto de negocio (nombre duplicado)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, client_id: str):
        """Actualizar campos de un cliente (PATCH parcial)"""
        from flask import request
        uid = parse_uuid(client_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de cliente invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            client = repo.get_by_id(uid, include_sensitive=True)
            if not client:
                return {"error": "not_found", "message": "Cliente no encontrado"}, 404
            if "name" in data:
                new_name = str(data["name"]).strip()
                if not new_name:
                    return {"error": "validation_error", "message": "El nombre no puede estar vacio"}, 400
                if new_name != client.name:
                    _svc.validate_unique_name(new_name, existing_id=client.id, repo=repo)
            billing, billing_error = _parse_billing(data)
            if billing_error:
                return {"error": "validation_error", "message": billing_error}, 400
            for field in ("name", "contact_name", "contact_email", "contact_phone", "vpn_ips", "vpn_credentials", "notes"):
                if field in data:
                    setattr(client, field, data[field])
            for field, value in billing.items():
                setattr(client, field, value)
            updated = repo.update(client)
            return _client_to_dict(updated, include_sensitive=True), 200
        except ClientBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:client_id>/deactivate")
@ns.param("client_id", "UUID del cliente")
class ClientDeactivate(Resource):
    @ns.doc("deactivate_client")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Cliente desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(409, "El cliente ya está inactivo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, client_id: str):
        """Desactivar un cliente. Incluye conteo de proyectos activos afectados."""
        uid = parse_uuid(client_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de cliente invalido"}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            proj_repo = ProjectRepository(db)
            client = repo.get_by_id(uid)
            if not client:
                return {"error": "not_found", "message": "Cliente no encontrado"}, 404
            if not client.active:
                return {"error": "already_inactive", "message": "El cliente ya esta inactivo"}, 409
            impact = _svc.get_deactivation_impact(uid, projects_repo=proj_repo)
            repo.deactivate(uid)
            result = {"id": client_id, "active": False, **impact}
            if impact.get("active_projects_count", 0) > 0:
                result["warning"] = f"Cliente desactivado. Tenia {impact['active_projects_count']} proyecto(s) activo(s)."
            return result, 200
        except Exception:
            return server_error()


@ns.route("/<string:client_id>/activate")
@ns.param("client_id", "UUID del cliente")
class ClientActivate(Resource):
    @ns.doc("activate_client")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Cliente activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(409, "El cliente ya está activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, client_id: str):
        """Activar un cliente previamente desactivado"""
        uid = parse_uuid(client_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de cliente invalido"}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            client = repo.get_by_id(uid)
            if not client:
                return {"error": "not_found", "message": "Cliente no encontrado"}, 404
            if client.active:
                return {"error": "already_active", "message": "El cliente ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": client_id, "active": True}, 200
        except Exception:
            return server_error()


@ns.route("/<string:client_id>/systems")
@ns.param("client_id", "UUID del cliente")
class ClientSystems(Resource):
    @ns.doc("list_client_systems")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Portafolio de software del cliente", _system_list_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, client_id: str):
        """Listar los sistemas de software del cliente (FR-029, SDD V3)"""
        uid = parse_uuid(client_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de cliente invalido"}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            if not repo.get_by_id(uid):
                return {"error": "not_found", "message": "Cliente no encontrado"}, 404
            items = [_system_to_dict(s) for s in repo.list_systems(uid)]
            return {"items": items, "total": len(items)}, 200
        except Exception:
            return server_error()

    @ns.doc("add_client_system")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_system_input, validate=False)
    @ns.response(201, "Sistema agregado", _system_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Cliente no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self, client_id: str):
        """Agregar un sistema al portafolio del cliente"""
        from flask import request
        uid = parse_uuid(client_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de cliente invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        system_type = str(data.get("system_type", "")).strip()
        brand = str(data.get("brand", "")).strip()
        if not system_type or not brand:
            return {"error": "validation_error", "message": "Los campos 'system_type' y 'brand' son requeridos"}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            if not repo.get_by_id(uid):
                return {"error": "not_found", "message": "Cliente no encontrado"}, 404
            system = ClientSystem.create(
                client_id=uid, system_type=system_type, brand=brand,
                version=data.get("version"), notes=data.get("notes"),
            )
            created = repo.add_system(system)
            return _system_to_dict(created), 201
        except Exception:
            return server_error()


@ns.route("/<string:client_id>/systems/<string:system_id>")
@ns.param("client_id", "UUID del cliente")
@ns.param("system_id", "UUID del sistema")
class ClientSystemDetail(Resource):
    @ns.doc("delete_client_system")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(204, "Sistema eliminado")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Cliente o sistema no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def delete(self, client_id: str, system_id: str):
        """Eliminar un sistema del portafolio del cliente"""
        uid = parse_uuid(client_id)
        sid = parse_uuid(system_id)
        if not uid or not sid:
            return {"error": "validation_error", "message": "ID invalido"}, 400
        try:
            db = get_db()
            repo = ClientRepository(db)
            if not repo.delete_system(uid, sid):
                return {"error": "not_found", "message": "Sistema no encontrado para ese cliente"}, 404
            return "", 204
        except Exception:
            return server_error()


# ── Enforcement FR-022 (spec 002): JWT + permiso por módulo/acción ─────────────
from backend.api.middleware.rbac import enforce_module as _enforce

for _cls in (ClientList, ClientDetail, ClientDeactivate, ClientActivate,
             ClientSystems, ClientSystemDetail):
    _cls.method_decorators = [_enforce("clients")]
