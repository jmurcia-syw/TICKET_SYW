"""Alta y consulta de Encargados: usuarios de rol "Encargado" vinculados a un Cliente fijo
(FR-007/007b). Solo Admin/Coordinador (permiso `client_contacts:manage`).
"""
import re
import secrets
import uuid

from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission, require_authenticated, current_user_has
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.client_contact import ClientContact
from backend.domain.entities.user import User
from backend.domain.errors import DomainError
from backend.domain.services.auth_service import AuthService
from backend.domain.services.client_contact_service import ClientContactService
from backend.infra.database import get_db
from backend.infra.repositories.client_contact_repo import ClientContactRepository
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.repositories.user_repo import UserRepository

ns = Namespace("client-contacts", description="Alta y consulta de Encargados (rol cliente externo)",
              path="/api/client-contacts")

_svc = ClientContactService()
_auth_svc = AuthService()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_error = error_model(ns, "ClientContactError")

_client_contact_input = ns.model("ClientContactInput", {
    "email": fields.String(required=True, description="Email real del contacto (dominio libre, no @sywork.net)"),
    "username": fields.String(required=True),
    "client_id": fields.String(required=True, description="UUID del Cliente al que queda vinculado"),
})

_client_contact_out = ns.model("ClientContact", {
    "id": fields.String(description="UUID de la fila client_contacts"),
    "user_id": fields.String(),
    "client_id": fields.String(),
    "email": fields.String(),
    "username": fields.String(),
    "client_name": fields.String(),
    "created_at": fields.String(),
})

_client_contact_list_out = ns.model("ClientContactList", {
    "items": fields.List(fields.Nested(_client_contact_out)),
    "total": fields.Integer(),
    "page": fields.Integer(),
    "page_size": fields.Integer(),
})

_client_contact_create_out = ns.model("ClientContactCreateResult", {
    "id": fields.String(),
    "user_id": fields.String(),
    "client_id": fields.String(),
    "email": fields.String(),
    "client_name": fields.String(),
    "provisional_password": fields.String(description="Contraseña provisional en texto plano — se muestra una única vez"),
})


def _to_dict(contact: ClientContact, user, client) -> dict:
    return {
        "id": str(contact.id),
        "user_id": str(contact.user_id),
        "client_id": str(contact.client_id),
        "email": user.email if user else None,
        "username": user.username if user else None,
        "client_name": client.name if client else None,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


@ns.route("")
class ClientContactList(Resource):
    @ns.doc("list_client_contacts", params={
        "client_id": {"description": "Filtrar por UUID de cliente", "type": "string"},
        "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
        "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
    })
    @ns.response(200, "Listado de Encargados con su Cliente asociado", _client_contact_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso client_contacts:manage, tickets:create ni tickets:edit", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self):
        """Listado paginado de Encargados, opcionalmente filtrado por Cliente. Además de
        `client_contacts:manage` (Admin/Coordinador), lo puede consultar cualquier rol con
        `tickets:create` o `tickets:edit` (Fase 2.2 — necesitan poder elegir el Encargado
        solicitante de un cliente al crear o editar un ticket)."""
        if not (current_user_has("client_contacts", "manage")
                or current_user_has("tickets", "create") or current_user_has("tickets", "edit")):
            return {"error": "forbidden", "message": "Acceso denegado"}, 403
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        client_id = parse_uuid(request.args.get("client_id") or "") or None
        try:
            db = get_db()
            items, total = ClientContactRepository(db).list_paginated(
                page=page, page_size=page_size, client_id=client_id)
            users_repo, clients_repo = UserRepository(db), ClientRepository(db)
            result = [
                _to_dict(c, users_repo.get_by_id(c.user_id), clients_repo.get_by_id(c.client_id))
                for c in items
            ]
            return {"items": result, "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_client_contact")
    @ns.expect(_client_contact_input, validate=False)
    @ns.response(201, "Encargado creado (usuario + vínculo con Cliente), contraseña provisional en texto plano", _client_contact_create_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso client_contacts:manage", _error)
    @ns.response(404, "Cliente no encontrado o inactivo", _error)
    @ns.response(409, "Email ya en uso", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("client_contacts", "manage")
    def post(self):
        """Crea la cuenta de acceso (rol Encargado) y su vínculo con el Cliente, atómicamente"""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        email = (data.get("email") or "").strip().lower()
        username = (data.get("username") or "").strip()
        client_id = parse_uuid(data.get("client_id", ""))
        if not email or not _EMAIL_RE.match(email):
            return {"error": "validation_error", "message": "El campo 'email' es requerido y debe ser un email válido"}, 400
        if not username:
            return {"error": "validation_error", "message": "El campo 'username' es requerido"}, 400
        if not client_id:
            return {"error": "validation_error", "message": "El campo 'client_id' es requerido y debe ser un UUID"}, 400
        try:
            db = get_db()
            users_repo = UserRepository(db)
            clients_repo = ClientRepository(db)
            role_repo = RoleRepository(db)
            _svc.validate_create(client_id=client_id, email=email, clients_repo=clients_repo, users_repo=users_repo)
            if users_repo.get_by_username_or_email(username):
                return {"error": "email_in_use", "message": "Ya existe un usuario con ese nombre de usuario"}, 409
            role = role_repo.get_by_name("Encargado")
            if not role:
                return {"error": "role_not_configured", "message": "El rol Encargado no está configurado"}, 500
            provisional_password = secrets.token_urlsafe(9)
            new_user = User(
                id=uuid.uuid4(), email=email, username=username, role=role,
                password_hash=_auth_svc.hash_password(provisional_password),
            )
            created_user = users_repo.create(new_user)
            contact = ClientContact(id=uuid.uuid4(), user_id=created_user.id, client_id=client_id)
            created_contact = ClientContactRepository(db).create(contact)
            client = clients_repo.get_by_id(client_id)
            return (
                {
                    "id": str(created_contact.id),
                    "user_id": str(created_user.id),
                    "client_id": str(client_id),
                    "email": created_user.email,
                    "client_name": client.name if client else None,
                    "provisional_password": provisional_password,
                },
                201,
                {"Location": f"/api/client-contacts/{created_contact.id}"},
            )
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
