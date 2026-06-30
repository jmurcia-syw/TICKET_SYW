from flask import Blueprint, jsonify, request
from backend.api.middleware.rbac import require_role
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.database import get_db
from backend.domain.entities.project import Project
from backend.domain.services.project_service import ProjectService, ProjectBusinessError
from datetime import date
import uuid

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")
_svc = ProjectService()


def _project_to_dict(project: Project, client_name: str | None = None) -> dict:
    d = {
        "id": str(project.id),
        "client_id": str(project.client_id),
        "name": project.name,
        "description": project.description,
        "active": project.active,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date_estimated": project.end_date_estimated.isoformat() if project.end_date_estimated else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }
    if client_name:
        d["client_name"] = client_name
    return d


@projects_bp.route("", methods=["GET"])
@require_role("admin", "coordinator")
def list_projects():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    client_id_str = request.args.get("client_id")
    search = request.args.get("search")
    active_param = request.args.get("active")
    active = None if active_param is None else active_param.lower() == "true"
    client_id = uuid.UUID(client_id_str) if client_id_str else None

    db = next(get_db())
    repo = ProjectRepository(db)
    client_repo = ClientRepository(db)
    items, total = repo.list_paginated(page=page, page_size=page_size, client_id=client_id, search=search, active=active)

    results = []
    for p in items:
        client = client_repo.get_by_id(p.client_id)
        results.append(_project_to_dict(p, client_name=client.name if client else None))

    return jsonify({"items": results, "total": total, "page": page, "page_size": page_size}), 200


@projects_bp.route("/<project_id>", methods=["GET"])
@require_role("admin", "coordinator")
def get_project(project_id: str):
    db = next(get_db())
    repo = ProjectRepository(db)
    project = repo.get_by_id(uuid.UUID(project_id))
    if not project:
        return jsonify({"error": "not_found", "message": "Proyecto no encontrado"}), 404
    return jsonify(_project_to_dict(project)), 200


@projects_bp.route("", methods=["POST"])
@require_role("admin", "coordinator")
def create_project():
    data = request.get_json(silent=True) or {}
    required = ("client_id", "name", "start_date")
    for field in required:
        if not data.get(field):
            return jsonify({"error": "validation_error", "message": f"El campo '{field}' es requerido"}), 400

    try:
        client_id = uuid.UUID(data["client_id"])
        start_date = date.fromisoformat(data["start_date"])
        end_date = date.fromisoformat(data["end_date_estimated"]) if data.get("end_date_estimated") else None
    except (ValueError, KeyError) as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400

    db = next(get_db())
    try:
        _svc.validate_create(
            client_id=client_id, name=data["name"], start_date=start_date, end_date=end_date,
            clients_repo=ClientRepository(db), projects_repo=ProjectRepository(db),
        )
    except ProjectBusinessError as e:
        return jsonify({"error": e.code, "message": e.message}), 400

    project = Project.create(
        client_id=client_id, name=data["name"], start_date=start_date,
        description=data.get("description"), end_date_estimated=end_date,
    )
    created = ProjectRepository(db).create(project)
    return jsonify(_project_to_dict(created)), 201


@projects_bp.route("/<project_id>", methods=["PATCH"])
@require_role("admin", "coordinator")
def update_project(project_id: str):
    db = next(get_db())
    repo = ProjectRepository(db)
    project = repo.get_by_id(uuid.UUID(project_id))
    if not project:
        return jsonify({"error": "not_found", "message": "Proyecto no encontrado"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "active"):
        if field in data:
            setattr(project, field, data[field])
    if "start_date" in data:
        project.start_date = date.fromisoformat(data["start_date"])
    if "end_date_estimated" in data:
        project.end_date_estimated = date.fromisoformat(data["end_date_estimated"]) if data["end_date_estimated"] else None
    updated = repo.update(project)
    return jsonify(_project_to_dict(updated)), 200


@projects_bp.route("/<project_id>/deactivate", methods=["PATCH"])
@require_role("admin", "coordinator")
def deactivate_project(project_id: str):
    db = next(get_db())
    repo = ProjectRepository(db)
    project = repo.deactivate(uuid.UUID(project_id))
    if not project:
        return jsonify({"error": "not_found", "message": "Proyecto no encontrado"}), 404
    return jsonify({"id": project_id, "active": False}), 200
