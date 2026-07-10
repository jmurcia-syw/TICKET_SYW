"""Alta y consulta de Usuarios/cliente: usuarios de rol "Usuario/cliente" (antes "Encargado",
spec 010) vinculados a un Cliente fijo (FR-007/007b). Solo Admin/Coordinador (permiso
`client_contacts:manage`).
"""
import re
import secrets
import uuid

from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission, require_authenticated, current_user_has
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.client_contact import ClientContact
from backend.domain.entities.user import User, USUARIO_CLIENTE_ROLE_NAME
from backend.domain.errors import DomainError
from backend.domain.services.auth_service import AuthService
from backend.domain.services.client_contact_service import ClientContactService
from backend.infra.database import get_db
from backend.infra.repositories.client_contact_repo import ClientContactRepository
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.repositories.user_repo import UserRepository

ns = Namespace("client-contacts", description="Alta y consulta de Usuarios/cliente (rol cliente externo)",
              path="/api/client-contacts")

_svc = ClientContactService()
_auth_svc = AuthService()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_error = error_model(ns, "ClientContactError")

_client_contact_input = ns.model("ClientContactInput", {
    "email": fields.String(required=True, description="Email real del contacto (dominio libre, no @sywork.net)"),
    "username": fields.String(required=True),
    "project_id": fields.String(description="UUID del Proyecto al que queda vinculado (spec 010: "
                                            "la relación operativa es con el Proyecto; el Cliente "
                                            "se deriva del proyecto y la membresía se crea "
                                            "automáticamente). Requerido si no viene client_id."),
    "client_id": fields.String(description="UUID del Cliente (forma legada, spec 007 — solo si "
                                           "no se envía project_id)"),
})

_contact_project_ref = ns.model("ContactProjectRef", {
    "id": fields.String(description="UUID del proyecto"),
    "name": fields.String(),
})

_client_contact_out = ns.model("ClientContact", {
    "id": fields.String(description="UUID de la fila client_contacts"),
    "user_id": fields.String(),
    "client_id": fields.String(),
    "email": fields.String(),
    "username": fields.String(),
    "client_name": fields.String(),
    "projects": fields.List(fields.Nested(_contact_project_ref),
                            description="Proyectos vinculados vía personal del proyecto (spec 010)"),
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


def _to_dict(contact: ClientContact, user, client, projects: list[dict] | None = None) -> dict:
    return {
        "id": str(contact.id),
        "user_id": str(contact.user_id),
        "client_id": str(contact.client_id),
        "email": user.email if user else None,
        "username": user.username if user else None,
        "client_name": client.name if client else None,
        "projects": projects or [],
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


@ns.route("")
class ClientContactList(Resource):
    @ns.doc("list_client_contacts", params={
        "client_id": {"description": "Filtrar por UUID de cliente", "type": "string"},
        "project_id": {"description": "Filtrar por UUID de proyecto: solo Usuarios/cliente que "
                                       "son personal del proyecto (spec 010) — fuente del "
                                       "selector de solicitante del ticket", "type": "string"},
        "email": {"description": "Filtrar por email (búsqueda parcial, sin distinguir mayúsculas)",
                  "type": "string"},
        "username": {"description": "Filtrar por nombre de usuario (búsqueda parcial)",
                     "type": "string"},
        "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
        "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
    })
    @ns.response(200, "Listado de Usuarios/cliente con su Cliente asociado", _client_contact_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso client_contacts:manage, tickets:create ni tickets:edit", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self):
        """Listado paginado de Usuarios/cliente, opcionalmente filtrado por Cliente. Además de
        `client_contacts:manage` (Admin/Coordinador), lo puede consultar cualquier rol con
        `tickets:create` o `tickets:edit` (Fase 2.2 — necesitan poder elegir el Usuario/cliente
        solicitante al crear o editar un ticket)."""
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
        project_id = parse_uuid(request.args.get("project_id") or "") or None
        email = (request.args.get("email") or "").strip() or None
        username = (request.args.get("username") or "").strip() or None
        try:
            db = get_db()
            items, total = ClientContactRepository(db).list_paginated(
                page=page, page_size=page_size, client_id=client_id, project_id=project_id,
                email=email, username=username)
            users_repo, clients_repo = UserRepository(db), ClientRepository(db)
            from backend.infra.repositories.project_member_repo import ProjectMemberRepository
            projects_by_user = ProjectMemberRepository(db).map_projects_by_user_ids(
                [c.user_id for c in items])
            result = [
                _to_dict(c, users_repo.get_by_id(c.user_id), clients_repo.get_by_id(c.client_id),
                         projects=projects_by_user.get(c.user_id))
                for c in items
            ]
            return {"items": result, "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_client_contact")
    @ns.expect(_client_contact_input, validate=False)
    @ns.response(201, "Usuario/cliente creado (usuario + vínculo al Proyecto con Cliente derivado, "
                      "o vínculo directo con Cliente en la forma legada), contraseña provisional "
                      "en texto plano", _client_contact_create_out)
    @ns.response(400, "Datos inválidos (se requiere project_id o client_id)", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso client_contacts:manage", _error)
    @ns.response(404, "Proyecto o Cliente no encontrado o inactivo", _error)
    @ns.response(409, "Email ya en uso, o proyecto inactivo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("client_contacts", "manage")
    def post(self):
        """Crea la cuenta de acceso (rol Usuario/cliente) vinculada a un **Proyecto** (spec 010:
        la relación operativa es con el Proyecto — el Cliente se deriva del proyecto y la
        membresía en el personal del proyecto se crea automáticamente). `client_id` directo se
        mantiene como forma legada (spec 007) para contactos aún sin proyecto."""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        email = (data.get("email") or "").strip().lower()
        username = (data.get("username") or "").strip()
        project_id = parse_uuid(data.get("project_id", "")) if data.get("project_id") else None
        client_id = parse_uuid(data.get("client_id", "")) if data.get("client_id") else None
        if not email or not _EMAIL_RE.match(email):
            return {"error": "validation_error", "message": "El campo 'email' es requerido y debe ser un email válido"}, 400
        if not username:
            return {"error": "validation_error", "message": "El campo 'username' es requerido"}, 400
        if not project_id and not client_id:
            return {"error": "validation_error",
                    "message": "Se requiere 'project_id' (el Cliente se deriva del proyecto) "
                               "o 'client_id' (forma legada)"}, 400
        try:
            db = get_db()
            users_repo = UserRepository(db)
            clients_repo = ClientRepository(db)
            role_repo = RoleRepository(db)
            if project_id:
                from backend.infra.repositories.project_repo import ProjectRepository
                project = ProjectRepository(db).get_by_id(project_id)
                if not project:
                    return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
                if not project.active:
                    return {"error": "project_inactive", "message": "El proyecto está inactivo"}, 409
                client_id = project.client_id
            _svc.validate_create(client_id=client_id, email=email, clients_repo=clients_repo, users_repo=users_repo)
            if users_repo.get_by_username_or_email(username):
                return {"error": "email_in_use", "message": "Ya existe un usuario con ese nombre de usuario"}, 409
            role = role_repo.get_by_name(USUARIO_CLIENTE_ROLE_NAME)
            if not role:
                return {"error": "role_not_configured",
                        "message": "El rol Usuario/cliente no está configurado"}, 500
            provisional_password = secrets.token_urlsafe(9)
            new_user = User(
                id=uuid.uuid4(), email=email, username=username, role=role,
                password_hash=_auth_svc.hash_password(provisional_password),
            )
            created_user = users_repo.create(new_user)
            contact = ClientContact(id=uuid.uuid4(), user_id=created_user.id, client_id=client_id)
            created_contact = ClientContactRepository(db).create(contact)
            if project_id:
                # Spec 010: la relación operativa es con el Proyecto — membresía automática
                from backend.domain.entities.project_member import ProjectMember
                from backend.infra.repositories.project_member_repo import ProjectMemberRepository
                ProjectMemberRepository(db).create(
                    ProjectMember.create(project_id=project_id, user_id=created_user.id))
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


_my_project_out = ns.model("MyProject", {
    "id": fields.String(description="UUID del proyecto"),
    "name": fields.String(),
    "client_id": fields.String(),
    "active": fields.Boolean(),
})

_my_projects_out = ns.model("MyProjectList", {
    "items": fields.List(fields.Nested(_my_project_out)),
    "total": fields.Integer(),
})


@ns.route("/me/projects")
class MyProjects(Resource):
    @ns.doc("list_my_projects")
    @ns.response(200, "Proyectos a los que está vinculado el usuario autenticado (spec 010: "
                      "fuente del selector de proyecto del autoservicio)", _my_projects_out)
    @ns.response(401, "No autenticado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_authenticated()
    def get(self):
        """Proyectos vinculados del usuario autenticado vía personal del proyecto (spec 010,
        FR-007). Pensado para el Usuario/cliente en autoservicio, pero responde para cualquier
        usuario autenticado (devuelve sus propias membresías, nunca las de otro)."""
        from flask import g
        from backend.infra.repositories.project_member_repo import ProjectMemberRepository
        from backend.infra.repositories.project_repo import ProjectRepository
        try:
            db = get_db()
            project_ids = ProjectMemberRepository(db).list_project_ids_by_user(g.current_user.id)
            projects_repo = ProjectRepository(db)
            items = []
            for pid in project_ids:
                project = projects_repo.get_by_id(pid)
                if project and project.active:
                    items.append({"id": str(project.id), "name": project.name,
                                  "client_id": str(project.client_id), "active": project.active})
            items.sort(key=lambda p: p["name"])
            return {"items": items, "total": len(items)}, 200
        except Exception:
            return server_error()
