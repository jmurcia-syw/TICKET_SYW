from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.role_repo import PermissionRepository
from backend.infra.database import get_db
from backend.api.routes._shared import error_model, server_error

ns = Namespace("permissions", description="Gestión de permisos del sistema", path="/api/permissions")

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
