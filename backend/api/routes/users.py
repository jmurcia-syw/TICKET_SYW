import secrets
import uuid

from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.entities.user import User
from backend.domain.services.role_service import RoleService, RoleBusinessError
from backend.domain.services.auth_service import AuthService
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("users", description="Gestión de usuarios y roles del sistema", path="/api/users")
_svc = RoleService()
_auth_svc = AuthService()

ALLOWED_EMAIL_DOMAIN = "sywork.net"

_error = error_model(ns, "UserError")

_role_ref = ns.model("UserRoleRef", {
    "id": fields.String(description="UUID del rol"),
    "name": fields.String(description="Nombre del rol"),
})

_user_out = ns.model("User", {
    "id": fields.String(description="UUID del usuario"),
    "email": fields.String(description="Email corporativo (@sywork.net)"),
    "username": fields.String(description="Nombre de usuario"),
    "role": fields.Nested(_role_ref, description="Rol del sistema"),
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

_role_input = ns.model("RoleIdInput", {
    "role_id": fields.String(required=True, description="UUID del rol a asignar"),
})

_status_result = ns.model("UserStatusResult", {
    "id": fields.String(description="UUID del usuario"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})

_user_create_input = ns.model("UserCreateInput", {
    "email": fields.String(required=True, description="Email corporativo (@sywork.net)", example="nombre.apellido@sywork.net"),
    "username": fields.String(required=True, description="Nombre de usuario", example="nombre.apellido"),
    "role_id": fields.String(required=True, description="UUID del rol a asignar"),
})

_user_create_out = ns.model("UserCreateResult", {
    "user": fields.Nested(_user_out),
    "provisional_password": fields.String(description="Contraseña provisional en texto plano — se muestra una única vez"),
})


def _user_to_dict(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": {"id": str(user.role.id), "name": user.role.name},
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
            "role": {"description": "Filtrar por nombre de rol", "type": "string"},
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
            db = get_db()
            users, total = UserRepository(db).list_paginated(page=page, page_size=page_size, role=role_filter, active=active)
            return {"items": [_user_to_dict(u) for u in users], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_user")
    @ns.expect(_user_create_input, validate=False)
    @ns.response(201, "Usuario creado, con contraseña provisional en texto plano (única vez)", _user_create_out)
    @ns.response(400, "Datos inválidos o dominio de email incorrecto", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "Email o username duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un usuario nuevo con contraseña provisional generada (FR-018b). Solo Admin."""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        email = (data.get("email") or "").strip().lower()
        username = (data.get("username") or "").strip()
        role_id = parse_uuid(data.get("role_id", ""))
        if not email:
            return {"error": "validation_error", "message": "El campo 'email' es requerido"}, 400
        if not email.endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
            return {"error": "invalid_email_domain", "message": f"El email debe ser @{ALLOWED_EMAIL_DOMAIN}"}, 400
        if not username:
            return {"error": "validation_error", "message": "El campo 'username' es requerido"}, 400
        if not role_id:
            return {"error": "validation_error", "message": "El campo 'role_id' es requerido y debe ser un UUID"}, 400
        try:
            db = get_db()
            repo = UserRepository(db)
            role_repo = RoleRepository(db)
            role = role_repo.get_by_id(role_id)
            if not role:
                return {"error": "role_not_found", "message": "Rol no encontrado"}, 404
            if repo.get_by_email(email):
                return {"error": "email_duplicate", "message": f"Ya existe un usuario con el email {email}"}, 409
            if repo.get_by_username_or_email(username):
                return {"error": "username_duplicate", "message": f"Ya existe un usuario con el username {username}"}, 409
            provisional_password = secrets.token_urlsafe(9)
            new_user = User(
                id=uuid.uuid4(),
                email=email,
                username=username,
                role=role,
                password_hash=_auth_svc.hash_password(provisional_password),
            )
            created = repo.create(new_user)
            return (
                {"user": _user_to_dict(created), "provisional_password": provisional_password},
                201,
                {"Location": f"/api/users/{created.id}"},
            )
        except Exception:
            return server_error()


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
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = get_db()
            user = UserRepository(db).get_by_id(uid)
            if not user:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return _user_to_dict(user), 200
        except Exception:
            return server_error()


@ns.route("/<string:user_id>/role")
@ns.param("user_id", "UUID del usuario")
class UserRole(Resource):
    @ns.doc("change_role")
    @ns.expect(_role_input, validate=False)
    @ns.response(200, "Rol actualizado correctamente", _user_out)
    @ns.response(400, "UUID inválido o role_id faltante", _error)
    @ns.response(404, "Usuario o rol no encontrado", _error)
    @ns.response(409, "Conflicto de negocio (ej: ultimo admin activo)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Cambiar el rol de un usuario. No se puede degradar al ultimo administrador activo."""
        from flask import request
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        role_id = parse_uuid(data.get("role_id", ""))
        if not role_id:
            return {"error": "validation_error", "message": "El campo 'role_id' es requerido y debe ser un UUID"}, 400
        try:
            db = get_db()
            repo = UserRepository(db)
            role_repo = RoleRepository(db)
            new_role = role_repo.get_by_id(role_id)
            if not new_role:
                return {"error": "role_not_found", "message": "Rol no encontrado"}, 404
            _svc.validate_role_change(uid, new_role.name, users_repo=repo)
            updated = repo.update_role(uid, role_id)
            if not updated:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return _user_to_dict(updated), 200
        except RoleBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


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
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = get_db()
            repo = UserRepository(db)
            _svc.validate_deactivation(uid, users_repo=repo)
            updated = repo.set_active(uid, False)
            if not updated:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return {"id": user_id, "active": False}, 200
        except RoleBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


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
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = get_db()
            repo = UserRepository(db)
            user = repo.get_by_id(uid)
            if not user:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            if user.active:
                return {"error": "already_active", "message": "El usuario ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": user_id, "active": True}, 200
        except Exception:
            return server_error()


# ── Enforcement FR-022 (spec 002): JWT + permiso por módulo/acción ─────────────
from backend.api.middleware.rbac import enforce_module as _enforce

for _cls in (UserList, UserDetail, UserRole, UserDeactivate, UserActivate):
    _cls.method_decorators = [_enforce("users")]
