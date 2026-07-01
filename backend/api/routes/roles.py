from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.entities.role import Role
from backend.domain.services.role_admin_service import RoleAdminService, RoleAdminError
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("roles", description="Gestión de roles y sus permisos", path="/api/roles")
_svc = RoleAdminService()

_error = error_model(ns, "RoleError")

_permission_ref = ns.model("RolePermissionRef", {
    "id": fields.String(description="UUID del permiso"),
    "module": fields.String(description="Módulo"),
    "action": fields.String(description="Acción"),
})

_role_out = ns.model("Role", {
    "id": fields.String(description="UUID del rol"),
    "name": fields.String(description="Nombre del rol"),
    "description": fields.String(description="Descripción"),
    "active": fields.Boolean(description="Estado activo"),
    "permissions": fields.List(fields.Nested(_permission_ref)),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_role_list_out = ns.model("RoleList", {
    "items": fields.List(fields.Nested(_role_out)),
    "total": fields.Integer(description="Total de roles"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_role_input = ns.model("RoleInput", {
    "name": fields.String(required=True, description="Nombre del rol", example="Auditor"),
    "description": fields.String(description="Descripción del rol"),
})

_role_update = ns.model("RoleUpdate", {
    "name": fields.String(description="Nuevo nombre"),
    "description": fields.String(description="Nueva descripción"),
})

_permissions_update = ns.model("RolePermissionsUpdate", {
    "permission_ids": fields.List(fields.String, required=True, description="Lista completa de UUIDs de permisos (reemplaza los actuales)"),
})

_status_result = ns.model("RoleStatusResult", {
    "id": fields.String(description="UUID del rol"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})


def _role_to_dict(role, repo: RoleRepository) -> dict:
    perms = repo.list_permissions_for_role(role.id)
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "active": role.active,
        "permissions": [{"id": str(p.id), "module": p.module, "action": p.action} for p in perms],
        "created_at": role.created_at.isoformat() if role.created_at else None,
    }


@ns.route("")
class RoleList(Resource):
    @ns.doc(
        "list_roles",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(200, "Listado de roles con sus permisos", _role_list_out)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar roles con sus permisos asignados"""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            items, total = repo.list_paginated(page=page, page_size=page_size, active=active)
            return {"items": [_role_to_dict(r, repo) for r in items], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_role")
    @ns.expect(_role_input, validate=False)
    @ns.response(201, "Rol creado", _role_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(409, "Nombre de rol duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un nuevo rol (sin permisos asignados; usar PUT .../permissions después)"""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        name = data.get("name", "").strip()
        if not name:
            return {"error": "validation_error", "message": "El campo 'name' es requerido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            if repo.get_by_name(name):
                return {"error": "name_duplicate", "message": f"Ya existe un rol con el nombre {name}"}, 409
            role = Role.create(name=name, description=data.get("description"))
            created = repo.create(role)
            return _role_to_dict(created, repo), 201, {"Location": f"/api/roles/{created.id}"}
        except Exception:
            return server_error()


@ns.route("/<string:role_id>")
@ns.param("role_id", "UUID del rol")
class RoleDetail(Resource):
    @ns.doc("get_role")
    @ns.response(200, "Detalle del rol", _role_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, role_id: str):
        """Obtener detalle de un rol incluyendo sus permisos"""
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            return _role_to_dict(role, repo), 200
        except Exception:
            return server_error()

    @ns.doc("update_role")
    @ns.expect(_role_update, validate=False)
    @ns.response(200, "Rol actualizado", _role_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "Nombre de rol duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, role_id: str):
        """Actualizar nombre/descripción de un rol"""
        from flask import request
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            if "name" in data:
                new_name = str(data["name"]).strip()
                if not new_name:
                    return {"error": "validation_error", "message": "El nombre no puede estar vacio"}, 400
                existing = repo.get_by_name(new_name)
                if existing and existing.id != role.id:
                    return {"error": "name_duplicate", "message": f"Ya existe un rol con el nombre {new_name}"}, 409
                role.name = new_name
            if "description" in data:
                role.description = data["description"]
            updated = repo.update(role)
            return _role_to_dict(updated, repo), 200
        except Exception:
            return server_error()


@ns.route("/<string:role_id>/permissions")
@ns.param("role_id", "UUID del rol")
class RolePermissions(Resource):
    @ns.doc("replace_role_permissions")
    @ns.expect(_permissions_update, validate=False)
    @ns.response(200, "Permisos actualizados (reemplaza lista completa)", _role_out)
    @ns.response(400, "UUID inválido o cuerpo incorrecto", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def put(self, role_id: str):
        """Reemplazar todos los permisos de un rol (operación de reemplazo total, no incremental)"""
        from flask import request
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        data = request.get_json(silent=True) or {}
        permission_ids = [parse_uuid(pid) for pid in data.get("permission_ids", [])]
        permission_ids = [p for p in permission_ids if p]
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.replace_permissions(uid, permission_ids)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            return _role_to_dict(role, repo), 200
        except Exception:
            return server_error()


@ns.route("/<string:role_id>/deactivate")
@ns.param("role_id", "UUID del rol")
class RoleDeactivate(Resource):
    @ns.doc("deactivate_role")
    @ns.response(200, "Rol desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "No se puede desactivar (rol Admin o con usuarios activos)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, role_id: str):
        """Desactivar un rol. Bloqueado para el rol Admin y para roles con usuarios activos asignados."""
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            if not role.active:
                return {"error": "already_inactive", "message": "El rol ya esta inactivo"}, 409
            _svc.validate_deactivation(role, users_repo=repo)
            repo.set_active(uid, False)
            return {"id": role_id, "active": False}, 200
        except RoleAdminError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:role_id>/activate")
@ns.param("role_id", "UUID del rol")
class RoleActivate(Resource):
    @ns.doc("activate_role")
    @ns.response(200, "Rol activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "El rol ya esta activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, role_id: str):
        """Activar un rol previamente desactivado"""
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            if role.active:
                return {"error": "already_active", "message": "El rol ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": role_id, "active": True}, 200
        except Exception:
            return server_error()
