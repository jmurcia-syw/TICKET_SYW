"""Autenticación: login provisional, Google OAuth2 y `/me`.

Documentado como Namespace de Flask-RESTX (antes era un Blueprint plano, invisible
en /swagger) para que aparezca en la documentación interactiva junto al resto de la
API, siguiendo /api-design-principles ("Documentation: Use OpenAPI/Swagger for
interactive docs"). Rutas públicas (sin JWT): /login y /google — son el punto de
entrada para obtenerlo. /me sí lo exige.
"""
import os

from flask import g, request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from backend.api.routes._shared import error_model
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.services.auth_service import AuthService

ns = Namespace("auth", description="Login provisional, Google OAuth2 y sesión actual", path="/api/auth")

ALLOWED_DOMAIN = "sywork.net"
_auth_svc = AuthService()

# ── Swagger models ────────────────────────────────────────────────────────────

_error = error_model(ns, "AuthError")

_permission_out = ns.model("AuthPermission", {
    "module": fields.String(description="Módulo del permiso", example="tickets"),
    "action": fields.String(description="Acción", example="view"),
})

_role_out = ns.model("AuthRole", {
    "id": fields.String(description="UUID del rol"),
    "name": fields.String(description="Nombre del rol", example="Coordinador"),
})

_user_out = ns.model("AuthUser", {
    "id": fields.String(description="UUID del usuario"),
    "email": fields.String(description="Email @sywork.net"),
    "username": fields.String(description="Nombre de usuario"),
    "role": fields.Nested(_role_out),
    "permissions": fields.List(fields.Nested(_permission_out), description="Permisos efectivos del rol"),
})

_login_input = ns.model("LoginInput", {
    "username_or_email": fields.String(required=True, description="Username o email @sywork.net", example="coordinador"),
    "password": fields.String(required=True, description="Contraseña"),
})

_google_input = ns.model("GoogleLoginInput", {
    "id_token": fields.String(required=True, description="ID token emitido por Google Identity Services"),
})

_auth_response = ns.model("AuthResponse", {
    "access_token": fields.String(description="JWT Bearer, expira en 8 horas"),
    "user": fields.Nested(_user_out),
})

_me_response = ns.model("MeResponse", {
    "user": fields.Nested(_user_out),
})


def _user_payload(user, db) -> dict:
    permissions = RoleRepository(db).list_permissions_for_role(user.role.id)
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": {"id": str(user.role.id), "name": user.role.name},
        "permissions": [{"module": p.module, "action": p.action} for p in permissions],
    }


# ── Rutas ─────────────────────────────────────────────────────────────────────

@ns.route("/login")
class AuthLogin(Resource):
    @ns.doc("login", security=None)
    @ns.expect(_login_input, validate=False)
    @ns.response(200, "Login exitoso", _auth_response)
    @ns.response(400, "Faltan credenciales", _error)
    @ns.response(401, "Usuario o contraseña incorrectos, o cuenta inactiva", _error)
    def post(self):
        """Login provisional por usuario/contraseña. Coexiste con /google, no lo reemplaza (ruta pública)."""
        data = request.get_json(silent=True) or {}
        identifier = (data.get("username_or_email") or "").strip()
        password = data.get("password") or ""
        if not identifier or not password:
            return {"error": "validation_error", "message": "username_or_email y password son requeridos"}, 400

        db = get_db()
        repo = UserRepository(db)
        user = repo.get_by_username_or_email(identifier)
        if not user or not user.active or not _auth_svc.verify_password(password, user.password_hash):
            return {"error": "unauthorized", "message": "Usuario o contraseña incorrectos"}, 401

        repo.update_last_login(user.id)
        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.name})
        return {"access_token": token, "user": _user_payload(user, db)}, 200


@ns.route("/google")
class AuthGoogle(Resource):
    @ns.doc("google_login", security=None)
    @ns.expect(_google_input, validate=False)
    @ns.response(200, "Login exitoso", _auth_response)
    @ns.response(400, "id_token faltante", _error)
    @ns.response(401, "Token inválido, dominio no permitido o usuario inexistente/inactivo", _error)
    def post(self):
        """Login vía Google OAuth2, restringido al dominio @sywork.net (ruta pública).

        No auto-crea usuarios: el email debe corresponder a una cuenta ya existente,
        dada de alta por un Admin (FR-018b).
        """
        data = request.get_json(silent=True) or {}
        id_token_str = data.get("id_token")
        if not id_token_str:
            return {"error": "bad_request", "message": "id_token requerido"}, 400

        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                os.environ.get("GOOGLE_CLIENT_ID"),
            )
        except ValueError:
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401

        email: str = idinfo.get("email", "")
        domain = email.split("@")[-1] if "@" in email else ""
        if domain != ALLOWED_DOMAIN:
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401

        google_sub: str = idinfo["sub"]
        db = get_db()
        repo = UserRepository(db)

        user = repo.get_by_google_sub(google_sub) or repo.get_by_email(email)
        if user is None or not user.active:
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401

        repo.update_last_login(user.id)
        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.name})
        return {"access_token": token, "user": _user_payload(user, db)}, 200


@ns.route("/me")
class AuthMe(Resource):
    @ns.doc("get_current_user")
    @ns.response(200, "Usuario autenticado", _me_response)
    @ns.response(401, "No autenticado, token inválido o cuenta desactivada", _error)
    def get(self):
        """Obtener el usuario y permisos de la sesión actual a partir del JWT."""
        from backend.api.middleware.auth import jwt_required_active

        @jwt_required_active
        def _inner():
            db = get_db()
            return {"user": _user_payload(g.current_user, db)}, 200

        try:
            return _inner()
        except Exception:
            # Token ausente/inválido: flask-restx convertiría la excepción de
            # flask-jwt-extended en 500 en vez de dejarla a JWTManager (FR-023).
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401
