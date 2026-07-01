import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ALLOWED_DOMAIN = "sywork.net"
_auth_svc = AuthService()


def _user_payload(user, db) -> dict:
    permissions = RoleRepository(db).list_permissions_for_role(user.role.id)
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": {"id": str(user.role.id), "name": user.role.name},
        "permissions": [{"module": p.module, "action": p.action} for p in permissions],
    }


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login provisional por usuario/contraseña. Coexiste con /google, no lo reemplaza."""
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username_or_email") or "").strip()
    password = data.get("password") or ""
    if not identifier or not password:
        return jsonify({"error": "validation_error", "message": "username_or_email y password son requeridos"}), 400

    db = next(get_db())
    repo = UserRepository(db)
    user = repo.get_by_username_or_email(identifier)
    if not user or not user.active or not _auth_svc.verify_password(password, user.password_hash):
        return jsonify({"error": "unauthorized", "message": "Usuario o contraseña incorrectos"}), 401

    repo.update_last_login(user.id)
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.name})
    payload = _user_payload(user, db)
    payload["access_token"] = token
    return jsonify(payload), 200


@auth_bp.route("/google", methods=["POST"])
def google_login():
    data = request.get_json(silent=True) or {}
    id_token_str = data.get("id_token")
    if not id_token_str:
        return jsonify({"error": "bad_request", "message": "id_token requerido"}), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            os.environ.get("GOOGLE_CLIENT_ID"),
        )
    except ValueError:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    email: str = idinfo.get("email", "")
    domain = email.split("@")[-1] if "@" in email else ""
    if domain != ALLOWED_DOMAIN:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    google_sub: str = idinfo["sub"]
    db = next(get_db())
    repo = UserRepository(db)

    user = repo.get_by_google_sub(google_sub) or repo.get_by_email(email)
    if user is None:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    if not user.active:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    repo.update_last_login(user.id)
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.name})
    payload = _user_payload(user, db)
    payload["access_token"] = token
    return jsonify(payload), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    from backend.api.middleware.auth import jwt_required_active
    from flask import g

    @jwt_required_active
    def _inner():
        db = next(get_db())
        return jsonify(_user_payload(g.current_user, db)), 200

    return _inner()
