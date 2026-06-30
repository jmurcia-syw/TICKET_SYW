from flask import Blueprint, g, jsonify, request
from backend.api.middleware.auth import jwt_required_active
from backend.api.middleware.rbac import require_role
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.database import get_db
from backend.domain.entities.client import Client
from backend.domain.services.client_service import ClientService, ClientBusinessError
import uuid

clients_bp = Blueprint("clients", __name__, url_prefix="/api/clients")
_svc = ClientService()


def _client_to_dict(client: Client, include_sensitive: bool = False) -> dict:
    d = {
        "id": str(client.id),
        "name": client.name,
        "slug": client.slug,
        "active": client.active,
        "contact_name": client.contact_name,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
        "notes": client.notes,
        "created_at": client.created_at.isoformat() if client.created_at else None,
        "updated_at": client.updated_at.isoformat() if client.updated_at else None,
    }
    if include_sensitive:
        d["vpn_ips"] = client.vpn_ips
        d["vpn_credentials"] = client.vpn_credentials
    return d


@clients_bp.route("", methods=["GET"])
@require_role("admin", "coordinator")
def list_clients():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    search = request.args.get("search")
    active_param = request.args.get("active")
    active = None if active_param is None else active_param.lower() == "true"

    db = next(get_db())
    repo = ClientRepository(db)
    items, total = repo.list_paginated(page=page, page_size=page_size, search=search, active=active)
    return jsonify({"items": [_client_to_dict(c) for c in items], "total": total, "page": page, "page_size": page_size}), 200


@clients_bp.route("/<client_id>", methods=["GET"])
@require_role("admin", "coordinator")
def get_client(client_id: str):
    db = next(get_db())
    repo = ClientRepository(db)
    client = repo.get_by_id(uuid.UUID(client_id), include_sensitive=True)
    if not client:
        return jsonify({"error": "not_found", "message": "Cliente no encontrado"}), 404
    return jsonify(_client_to_dict(client, include_sensitive=True)), 200


@clients_bp.route("", methods=["POST"])
@require_role("admin", "coordinator")
def create_client():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "validation_error", "message": "El nombre es requerido"}), 400

    db = next(get_db())
    repo = ClientRepository(db)
    try:
        _svc.validate_unique_name(name, repo=repo)
    except ClientBusinessError as e:
        return jsonify({"error": e.code, "message": e.message}), 400

    client = Client.create(
        name=name,
        contact_name=data.get("contact_name"),
        contact_email=data.get("contact_email"),
        contact_phone=data.get("contact_phone"),
        vpn_ips=data.get("vpn_ips"),
        vpn_credentials=data.get("vpn_credentials"),
        notes=data.get("notes"),
    )
    created = repo.create(client)
    return jsonify(_client_to_dict(created)), 201


@clients_bp.route("/<client_id>", methods=["PATCH"])
@require_role("admin", "coordinator")
def update_client(client_id: str):
    db = next(get_db())
    repo = ClientRepository(db, include_sensitive=True)
    client = repo.get_by_id(uuid.UUID(client_id), include_sensitive=True)
    if not client:
        return jsonify({"error": "not_found", "message": "Cliente no encontrado"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != client.name:
        try:
            _svc.validate_unique_name(data["name"], existing_id=client.id, repo=repo)
        except ClientBusinessError as e:
            return jsonify({"error": e.code, "message": e.message}), 400

    for field in ("name", "contact_name", "contact_email", "contact_phone", "vpn_ips", "vpn_credentials", "notes"):
        if field in data:
            setattr(client, field, data[field])

    updated = repo.update(client)
    return jsonify(_client_to_dict(updated)), 200


@clients_bp.route("/<client_id>/deactivate", methods=["PATCH"])
@require_role("admin")
def deactivate_client(client_id: str):
    db = next(get_db())
    repo = ClientRepository(db)
    proj_repo = ProjectRepository(db)
    client = repo.get_by_id(uuid.UUID(client_id))
    if not client:
        return jsonify({"error": "not_found", "message": "Cliente no encontrado"}), 404

    impact = _svc.get_deactivation_impact(uuid.UUID(client_id), projects_repo=proj_repo)
    repo.deactivate(uuid.UUID(client_id))
    result = {"id": client_id, "active": False, **impact}
    if impact["active_projects_count"] > 0:
        result["warning"] = f"El cliente tiene {impact['active_projects_count']} proyecto(s) activo(s)."
    return jsonify(result), 200
