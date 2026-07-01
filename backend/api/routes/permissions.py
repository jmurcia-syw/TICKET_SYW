from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.role_repo import RoleRepository, PermissionRepository
from backend.domain.entities.role import Permission
from backend.domain.services.role_admin_service import RoleAdminService, RoleAdminError
from backend.infra.database import get_db
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("permissions", description="Gestión de permisos del sistema", path="/api/permissions")

_svc = RoleAdminService()

_error = error_model(ns, "PermissionError")

_permission_out = ns.model("Permission", {
    "id": fields.String(description="UUID del permiso"),
    "module": fields.String(description="Módulo"),
    "action": fields.String(description="Acción"),
    "description": fields.String(description="Descripción"),
})

_permission_list_out = ns.model("PermissionList", {
    "items": fields.List(fields.Nested(_permission_out)),
    "total": fields.Integer(description="Total de permisos"),
})

_permission_input = ns.model("PermissionInput", {
    "module": fields.String(required=True, description="Módulo", example="clients"),
    "action": fields.String(required=True, description="Acción", example="view"),
    "description": fields.String(description="Descripción"),
})


def _permission_to_dict(permission) -> dict:
    return {
        "id": str(permission.id),
        "module": permission.module,
        "action": permission.action,
        "description": permission.description,
    }


@ns.route("")
class PermissionList(Resource):
    @ns.doc("list_permissions")
    @ns.response(200, "Listado de permisos del sistema", _permission_list_out)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar todos los permisos disponibles del sistema"""
        try:
            db = next(get_db())
            repo = PermissionRepository(db)
            items = repo.list_all()
            return {"items": [_permission_to_dict(p) for p in items], "total": len(items)}, 200
        except Exception:
            return server_error()

    @ns.doc("create_permission")
    @ns.expect(_permission_input, validate=False)
    @ns.response(201, "Permiso creado", _permission_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(409, "Combinación módulo+acción duplicada", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear una definición de permiso nueva (módulo + acción)"""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        module = data.get("module", "").strip()
        action = data.get("action", "").strip()
        if not module:
            return {"error": "validation_error", "message": "El campo 'module' es requerido"}, 400
        if not action:
            return {"error": "validation_error", "message": "El campo 'action' es requerido"}, 400
        try:
            db = next(get_db())
            repo = PermissionRepository(db)
            if repo.get_by_module_action(module, action):
                return {"error": "module_action_duplicate", "message": f"Ya existe el permiso {module}.{action}"}, 409
            permission = Permission.create(module=module, action=action, description=data.get("description"))
            created = repo.create(permission)
            return _permission_to_dict(created), 201, {"Location": f"/api/permissions/{created.id}"}
        except Exception:
            return server_error()


@ns.route("/<string:permission_id>")
@ns.param("permission_id", "UUID del permiso")
class PermissionDetail(Resource):
    @ns.doc("delete_permission")
    @ns.response(204, "Permiso eliminado correctamente")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(409, "No se puede eliminar: permiso asignado a algún rol", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def delete(self, permission_id: str):
        """Eliminar una definición de permiso. Retorna 409 si está asignado a algún rol."""
        uid = parse_uuid(permission_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de permiso invalido"}, 400
        try:
            db = next(get_db())
            perm_repo = PermissionRepository(db)
            role_repo = RoleRepository(db)
            _svc.validate_permission_delete(uid, roles_repo=role_repo)
            perm_repo.delete(uid)
            return "", 204
        except RoleAdminError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
