from flask import Blueprint, g, jsonify, request
from backend.api.middleware.auth import jwt_required_active
from backend.api.middleware.rbac import require_role
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.database import get_db
from backend.domain.entities.user import Role
from backend.domain.services.role_service import RoleService, RoleBusinessError
import uuid

users_bp = Blueprint("users", __name__, url_prefix="/api/users")
_svc = RoleService()


def _user_to_dict(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "active": user.active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@users_bp.route("", methods=["GET"])
@require_role("admin")
def list_users():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    role_filter = request.args.get("role")
    active_param = request.args.get("active")
    active = None if active_param is None else active_param.lower() == "true"

    db = next(get_db())
    users, total = UserRepository(db).list_paginated(page=page, page_size=page_size, role=role_filter, active=active)
    return jsonify({"items": [_user_to_dict(u) for u in users], "total": total, "page": page, "page_size": page_size}), 200


@users_bp.route("/me", methods=["GET"])
@jwt_required_active
def me():
    return jsonify(_user_to_dict(g.current_user)), 200


@users_bp.route("/<user_id>/role", methods=["PATCH"])
@require_role("admin")
def change_role(user_id: str):
    data = request.get_json(silent=True) or {}
    role_str = data.get("role", "").lower()
    try:
        new_role = Role(role_str)
    except ValueError:
        return jsonify({"error": "invalid_role", "message": "Rol inválido. Valores permitidos: admin, coordinator, qm, resolver"}), 400

    db = next(get_db())
    repo = UserRepository(db)
    try:
        _svc.validate_role_change(uuid.UUID(user_id), new_role, users_repo=repo)
    except RoleBusinessError as e:
        return jsonify({"error": e.code, "message": e.message}), 409

    updated = repo.update_role(uuid.UUID(user_id), new_role)
    if not updated:
        return jsonify({"error": "not_found", "message": "Usuario no encontrado"}), 404
    return jsonify(_user_to_dict(updated)), 200


@users_bp.route("/<user_id>/deactivate", methods=["PATCH"])
@require_role("admin")
def deactivate_user(user_id: str):
    db = next(get_db())
    repo = UserRepository(db)
    try:
        _svc.validate_deactivation(uuid.UUID(user_id), users_repo=repo)
    except RoleBusinessError as e:
        return jsonify({"error": e.code, "message": e.message}), 409

    updated = repo.set_active(uuid.UUID(user_id), False)
    if not updated:
        return jsonify({"error": "not_found", "message": "Usuario no encontrado"}), 404
    return jsonify({"id": user_id, "active": False}), 200
