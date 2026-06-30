from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.database import get_db
from backend.domain.entities.user import Role
from backend.domain.services.role_service import RoleService, RoleBusinessError
import uuid

ns = Namespace("users", description="Gestión de usuarios y roles del sistema", path="/api/users")
_svc = RoleService()

# ── Models ────────────────────────────────────────────────────────────────────

_error = ns.model("UserError", {
    "error": fields.String(description="Código de error", example="not_found"),
    "message": fields.String(description="Descripción del error"),
})

_user_out = ns.model("User", {
    "id": fields.String(description="UUID del usuario"),
    "email": fields.String(description="Email corporativo (@sywork.net)"),
    "role": fields.String(
        description="Rol del sistema",
        enum=["admin", "coordinator", "qm", "resolver"],
        example="coordinator",
    ),
    "active": fields.Boolean(description="Estado activo"),
    "last_login_at": fields.String(description="Último login ISO-8601 (null si nunca ha ingresado)"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_user_list_out = ns.model("UserList", {
    "items": fields.List(fields.Nested(_user_out)),
    "total": fields.Integer(description="Total de usuarios"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_role_input = ns.model("RoleInput", {
    "role": fields.String(
        required=True,
        description="Nuevo rol a asignar",
        enum=["admin", "coordinator", "qm", "resolver"],
        example="coordinator",
    ),
})

_status_result = ns.model("UserStatusResult", {
    "id": fields.String(description="UUID del usuario"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})


def _parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _user_to_dict(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "active": user.active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ── Resources ────────────────────────────────────────────────────────────────

@ns.route("")
class UserList(Resource):
    @ns.doc(
        "list_users",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "role": {
                "description": "Filtrar por rol: admin, coordinator, qm, resolver",
                "type": "string",
                "enum": ["admin", "coordinator", "qm", "resolver"],
            },
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(200, "Listado de usuarios del sistema", _user_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar usuarios del sistema con filtros por rol y estado"""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        role_filter = request.args.get("role")
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        try:
            db = next(get_db())
            users, total = UserRepository(db).list_paginated(page=page, page_size=page_size, role=role_filter, active=active)
            return {"items": [_user_to_dict(u) for u in users], "total": total, "page": page, "page_size": page_size}, 200
        except Exception as exc:
            return {"error": "server_error", "message": str(exc)}, 500


@ns.route("/<string:user_id>")
@ns.param("user_id", "UUID del usuario")
class UserDetail(Resource):
    @ns.doc("get_user")
    @ns.response(200, "Detalle del usuario", _user_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, user_id: str):
        """Obtener detalle de un usuario por ID"""
        uid = _parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = next(get_db())
            user = UserRepository(db).get_by_id(uid)
            if not user:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return _user_to_dict(user), 200
        except Exception as exc:
            return {"error": "server_error", "message": str(exc)}, 500


@ns.route("/<string:user_id>/role")
@ns.param("user_id", "UUID del usuario")
class UserRole(Resource):
    @ns.doc("change_role")
    @ns.expect(_role_input, validate=False)
    @ns.response(200, "Rol actualizado correctamente", _user_out)
    @ns.response(400, "UUID inválido o rol no reconocido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(409, "Conflicto de negocio (ej: ultimo admin activo)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Cambiar el rol de un usuario. No se puede degradar al ultimo administrador activo."""
        from flask import request
        uid = _parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        role_str = data.get("role", "").strip().lower()
        if not role_str:
            return {"error": "validation_error", "message": "El campo 'role' es requerido"}, 400
        try:
            new_role = Role(role_str)
        except ValueError:
            valid = [r.value for r in Role]
            return {"error": "invalid_role", "message": f"Rol invalido. Valores permitidos: {valid}"}, 400
        try:
            db = next(get_db())
            repo = UserRepository(db)
            _svc.validate_role_change(uid, new_role, users_repo=repo)
            updated = repo.update_role(uid, new_role)
            if not updated:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return _user_to_dict(updated), 200
        except RoleBusinessError as e:
            return {"error": e.code, "message": e.message}, 409
        except Exception as exc:
            return {"error": "server_error", "message": str(exc)}, 500


@ns.route("/<string:user_id>/deactivate")
@ns.param("user_id", "UUID del usuario")
class UserDeactivate(Resource):
    @ns.doc("deactivate_user")
    @ns.response(200, "Usuario desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(409, "No se puede desactivar (ej: ultimo admin activo)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Desactivar un usuario. No se puede desactivar al ultimo administrador activo."""
        uid = _parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = next(get_db())
            repo = UserRepository(db)
            _svc.validate_deactivation(uid, users_repo=repo)
            updated = repo.set_active(uid, False)
            if not updated:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return {"id": user_id, "active": False}, 200
        except RoleBusinessError as e:
            return {"error": e.code, "message": e.message}, 409
        except Exception as exc:
            return {"error": "server_error", "message": str(exc)}, 500


@ns.route("/<string:user_id>/activate")
@ns.param("user_id", "UUID del usuario")
class UserActivate(Resource):
    @ns.doc("activate_user")
    @ns.response(200, "Usuario activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(409, "El usuario ya esta activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Activar un usuario previamente desactivado"""
        uid = _parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = next(get_db())
            repo = UserRepository(db)
            user = repo.get_by_id(uid)
            if not user:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            if user.active:
                return {"error": "already_active", "message": "El usuario ya esta activo"}, 409
            updated = repo.set_active(uid, True)
            return _user_to_dict(updated), 200
        except Exception as exc:
            return {"error": "server_error", "message": str(exc)}, 500
