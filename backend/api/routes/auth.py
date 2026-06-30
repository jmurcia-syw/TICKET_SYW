import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.database import get_db
from backend.domain.entities.user import User, Role
import uuid

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ALLOWED_DOMAIN = "sywork.net"


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
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.value})
    return jsonify({"access_token": token, "role": user.role.value, "email": user.email}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    from backend.api.middleware.auth import jwt_required_active
    from flask import g

    @jwt_required_active
    def _inner():
        u = g.current_user
        return jsonify({"id": str(u.id), "email": u.email, "role": u.role.value, "active": u.active}), 200

    return _inner()
