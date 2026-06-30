from flask import Blueprint, g, jsonify, request
from backend.api.middleware.auth import jwt_required_active
from backend.api.middleware.rbac import require_role
from backend.infra.repositories.resource_repo import ResourceRepository, SkillRepository
from backend.infra.database import get_db
from backend.domain.entities.resource import Resource, Skill
from backend.domain.services.skill_service import SkillService, SkillBusinessError
import uuid

resources_bp = Blueprint("resources", __name__, url_prefix="/api")
_skill_svc = SkillService()


def _resource_to_dict(resource: Resource) -> dict:
    return {
        "id": str(resource.id),
        "user_id": str(resource.user_id) if resource.user_id else None,
        "full_name": resource.full_name,
        "email": resource.email,
        "active": resource.active,
        "notes": resource.notes,
        "skills": [{"id": str(s.id), "code": s.code, "label": s.label} for s in resource.skills],
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
    }


# ── Skills ─────────────────────────────────────────────────────────────────

@resources_bp.route("/skills", methods=["GET"])
@jwt_required_active
def list_skills():
    active_param = request.args.get("active", "true")
    active = None if active_param == "all" else active_param.lower() == "true"
    db = next(get_db())
    skills = SkillRepository(db).list_all(active=active)
    return jsonify({"items": [{"id": str(s.id), "code": s.code, "label": s.label, "active": s.active} for s in skills], "total": len(skills)}), 200


@resources_bp.route("/skills", methods=["POST"])
@require_role("admin")
def create_skill():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip().upper()
    label = data.get("label", "").strip()
    if not code or not label:
        return jsonify({"error": "validation_error", "message": "Código y etiqueta son requeridos"}), 400

    db = next(get_db())
    repo = SkillRepository(db)
    if repo.get_by_code(code):
        return jsonify({"error": "code_duplicate", "message": "Ya existe un skill con ese código"}), 400

    skill = Skill.create(code=code, label=label)
    created = repo.create(skill)
    return jsonify({"id": str(created.id), "code": created.code, "label": created.label, "active": created.active}), 201


@resources_bp.route("/skills/<skill_id>", methods=["DELETE"])
@require_role("admin")
def delete_skill(skill_id: str):
    db = next(get_db())
    skill_repo = SkillRepository(db)
    try:
        _skill_svc.validate_delete(uuid.UUID(skill_id), resources_repo=skill_repo)
    except SkillBusinessError as e:
        return jsonify({"error": e.code, "message": e.message, **e.extra}), 409
    skill_repo.delete(uuid.UUID(skill_id))
    return "", 204


# ── Resources ──────────────────────────────────────────────────────────────

@resources_bp.route("/resources", methods=["GET"])
@jwt_required_active
def list_resources():
    user = g.current_user
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    search = request.args.get("search")
    skill_code = request.args.get("skill_code")
    active_param = request.args.get("active")
    active = None if active_param is None else active_param.lower() == "true"

    db = next(get_db())
    repo = ResourceRepository(db)

    # Resolvers can only see their own resource
    if user.role.value == "resolver":
        own = repo.get_by_user_id(user.id)
        items = [own] if own else []
        return jsonify({"items": [_resource_to_dict(r) for r in items], "total": len(items), "page": 1, "page_size": page_size}), 200

    items, total = repo.list_paginated(page=page, page_size=page_size, search=search, skill_code=skill_code, active=active)
    return jsonify({"items": [_resource_to_dict(r) for r in items], "total": total, "page": page, "page_size": page_size}), 200


@resources_bp.route("/resources/<resource_id>", methods=["GET"])
@jwt_required_active
def get_resource(resource_id: str):
    user = g.current_user
    db = next(get_db())
    repo = ResourceRepository(db)
    resource = repo.get_by_id(uuid.UUID(resource_id))
    if not resource:
        return jsonify({"error": "not_found", "message": "Recurso no encontrado"}), 404
    if user.role.value == "resolver" and resource.user_id != user.id:
        return jsonify({"error": "forbidden", "message": "Acceso denegado"}), 403
    return jsonify(_resource_to_dict(resource)), 200


@resources_bp.route("/resources", methods=["POST"])
@require_role("admin")
def create_resource():
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    if not full_name or not email:
        return jsonify({"error": "validation_error", "message": "Nombre y email son requeridos"}), 400
    if not email.endswith("@sywork.net"):
        return jsonify({"error": "invalid_email_domain", "message": "El email debe ser @sywork.net"}), 400

    db = next(get_db())
    repo = ResourceRepository(db)
    if repo.get_by_email(email):
        return jsonify({"error": "email_duplicate", "message": "Ya existe un recurso con ese email"}), 400

    skill_ids = [uuid.UUID(sid) for sid in data.get("skill_ids", [])]
    skill_entities = [SkillRepository(db).get_by_id(sid) for sid in skill_ids]
    resource = Resource.create(
        full_name=full_name, email=email,
        user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
        notes=data.get("notes"),
        skills=[s for s in skill_entities if s],
    )
    created = repo.create(resource)
    return jsonify(_resource_to_dict(created)), 201


@resources_bp.route("/resources/<resource_id>", methods=["PATCH"])
@jwt_required_active
def update_resource(resource_id: str):
    user = g.current_user
    db = next(get_db())
    repo = ResourceRepository(db)
    resource = repo.get_by_id(uuid.UUID(resource_id))
    if not resource:
        return jsonify({"error": "not_found", "message": "Recurso no encontrado"}), 404

    data = request.get_json(silent=True) or {}

    if user.role.value == "resolver":
        if resource.user_id != user.id:
            return jsonify({"error": "forbidden", "message": "Acceso denegado"}), 403
        # Resolvers can only update notes
        allowed = {k: v for k, v in data.items() if k == "notes"}
        updated = repo.update(uuid.UUID(resource_id), **allowed)
    else:
        if user.role.value not in ("admin",):
            return jsonify({"error": "forbidden", "message": "Acceso denegado"}), 403
        allowed_fields = {k: v for k, v in data.items() if k in ("full_name", "notes", "active")}
        updated = repo.update(uuid.UUID(resource_id), **allowed_fields)

    return jsonify(_resource_to_dict(updated)), 200


@resources_bp.route("/resources/<resource_id>/skills", methods=["PATCH"])
@require_role("admin")
def update_resource_skills(resource_id: str):
    data = request.get_json(silent=True) or {}
    skill_ids = [uuid.UUID(sid) for sid in data.get("skill_ids", [])]
    db = next(get_db())
    resource = ResourceRepository(db).update_skills(uuid.UUID(resource_id), skill_ids)
    if not resource:
        return jsonify({"error": "not_found", "message": "Recurso no encontrado"}), 404
    return jsonify(_resource_to_dict(resource)), 200


@resources_bp.route("/resources/<resource_id>/deactivate", methods=["PATCH"])
@require_role("admin")
def deactivate_resource(resource_id: str):
    db = next(get_db())
    resource = ResourceRepository(db).deactivate(uuid.UUID(resource_id))
    if not resource:
        return jsonify({"error": "not_found", "message": "Recurso no encontrado"}), 404
    return jsonify({"id": resource_id, "active": False}), 200
