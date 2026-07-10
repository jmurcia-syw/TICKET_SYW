"""Personal del Proyecto y subgrupos "Equipo" (spec 010, US3 — estilo Teamwork).

Dos namespaces con prefijos distintos (mismo criterio que task_lists.py): rutas anidadas bajo
`/api/projects/{id}` y rutas propias `/api/project-teams/{id}`. Protegido por el módulo
`projects` existente vía `enforce_module` (GET→view, POST→create, PATCH/PUT→edit,
DELETE→deactivate): Coordinador/Admin gestionan, QM/Resolutor consultan (FR-012, research
Decisión 7).
"""
from flask import request
from flask_restx import Namespace, Resource, fields

from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.project_member import ProjectMember, ProjectTeam
from backend.domain.errors import DomainError
from backend.domain.services.project_member_service import ProjectMemberService
from backend.infra.database import get_db
from backend.infra.repositories.project_member_repo import ProjectMemberRepository
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.user_repo import UserRepository

ns_project_members = Namespace(
    "project-members", description="Personal asignado a un Proyecto (spec 010)",
    path="/api/projects")
ns_teams = Namespace(
    "project-teams", description='Subgrupos "Equipo" de un Proyecto (edición directa)',
    path="/api/project-teams")

_svc = ProjectMemberService()

_error = error_model(ns_project_members, "ProjectMemberError")

_member_out = ns_project_members.model("ProjectMember", {
    "id": fields.String(description="UUID de la asignación"),
    "project_id": fields.String(),
    "user_id": fields.String(),
    "full_name": fields.String(description="Nombre del recurso vinculado (fallback: username)"),
    "email": fields.String(),
    "role_name": fields.String(description="Rol del usuario (derivado, no almacenado)"),
    "assigned_at": fields.String(),
})

_member_list_out = ns_project_members.model("ProjectMemberList", {
    "items": fields.List(fields.Nested(_member_out)),
    "total": fields.Integer(),
})

_member_input = ns_project_members.model("ProjectMemberInput", {
    "user_id": fields.String(required=True, description="UUID del usuario a asignar"),
})

_team_member_out = ns_teams.model("ProjectTeamMember", {
    "member_id": fields.String(description="UUID de la asignación (project_members)"),
    "user_id": fields.String(),
    "full_name": fields.String(),
    "email": fields.String(),
    "role_name": fields.String(),
})

_team_out = ns_teams.model("ProjectTeam", {
    "id": fields.String(description="UUID del equipo"),
    "project_id": fields.String(),
    "name": fields.String(),
    "members": fields.List(fields.Nested(_team_member_out)),
    "member_count": fields.Integer(),
    "created_at": fields.String(),
})

_team_list_out = ns_teams.model("ProjectTeamList", {
    "items": fields.List(fields.Nested(_team_out)),
    "total": fields.Integer(),
})

_team_input = ns_teams.model("ProjectTeamInput", {
    "name": fields.String(required=True, description="Nombre único dentro del Proyecto"),
})

_team_members_input = ns_teams.model("ProjectTeamMembersInput", {
    "member_ids": fields.List(fields.String, required=True,
                              description="Lista completa de UUIDs de project_members "
                                          "(reemplaza el conjunto actual)"),
})


def _team_dict(repo: ProjectMemberRepository, team: ProjectTeam) -> dict:
    teams = repo.list_teams(team.project_id)
    for t in teams:
        if t["id"] == str(team.id):
            return t
    return {"id": str(team.id), "project_id": str(team.project_id), "name": team.name,
            "members": [], "member_count": 0,
            "created_at": team.created_at.isoformat() if team.created_at else None}


@ns_project_members.route("/<string:project_id>/members")
@ns_project_members.param("project_id", "UUID del Proyecto")
class ProjectMemberList(Resource):
    @ns_project_members.doc("list_project_members", params={
        "role_name": {"description": "Filtrar por nombre de rol (p. ej. Usuario/cliente)",
                      "type": "string"},
    })
    @ns_project_members.response(200, "Personal del proyecto con rol derivado", _member_list_out)
    @ns_project_members.response(400, "UUID inválido", _error)
    @ns_project_members.response(401, "No autenticado", _error)
    @ns_project_members.response(403, "Sin permiso projects:view", _error)
    @ns_project_members.response(404, "Proyecto no encontrado", _error)
    @ns_project_members.response(500, "Error interno del servidor", _error)
    def get(self, project_id: str):
        """Lista el personal asignado al proyecto (cualquier rol)"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        try:
            db = get_db()
            if not ProjectRepository(db).get_by_id(uid):
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            items = ProjectMemberRepository(db).list_by_project(
                uid, role_name=request.args.get("role_name") or None)
            return {"items": items, "total": len(items)}, 200
        except Exception:
            return server_error()

    @ns_project_members.doc("add_project_member")
    @ns_project_members.expect(_member_input, validate=False)
    @ns_project_members.response(201, "Persona asignada al proyecto", _member_out)
    @ns_project_members.response(400, "Datos inválidos", _error)
    @ns_project_members.response(401, "No autenticado", _error)
    @ns_project_members.response(403, "Sin permiso projects:create", _error)
    @ns_project_members.response(404, "Proyecto o usuario no encontrado", _error)
    @ns_project_members.response(409, "Ya asignado (already_member) o usuario desactivado "
                                       "(user_inactive)", _error)
    @ns_project_members.response(500, "Error interno del servidor", _error)
    def post(self, project_id: str):
        """Asigna un usuario activo al proyecto (asignación única por persona/proyecto)"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        data = request.get_json(silent=True)
        if not data or not data.get("user_id"):
            return {"error": "validation_error", "message": "El campo user_id es requerido"}, 400
        user_id = parse_uuid(data["user_id"])
        if not user_id:
            return {"error": "validation_error", "message": "user_id invalido"}, 400
        try:
            db = get_db()
            if not ProjectRepository(db).get_by_id(uid):
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            repo = ProjectMemberRepository(db)
            _svc.validate_assign(uid, user_id, users_repo=UserRepository(db), members_repo=repo)
            created = repo.create(ProjectMember.create(project_id=uid, user_id=user_id))
            items = repo.list_by_project(uid)
            member = next((m for m in items if m["id"] == str(created.id)), None)
            return member, 201, {"Location": f"/api/projects/{uid}/members/{created.id}"}
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns_project_members.route("/<string:project_id>/members/<string:member_id>")
@ns_project_members.param("project_id", "UUID del Proyecto")
@ns_project_members.param("member_id", "UUID de la asignación")
class ProjectMemberDetail(Resource):
    @ns_project_members.doc("remove_project_member")
    @ns_project_members.response(204, "Persona desasignada (sale también de todos los subgrupos)")
    @ns_project_members.response(400, "UUID inválido", _error)
    @ns_project_members.response(401, "No autenticado", _error)
    @ns_project_members.response(403, "Sin permiso projects:deactivate", _error)
    @ns_project_members.response(404, "Asignación no encontrada en este proyecto", _error)
    @ns_project_members.response(500, "Error interno del servidor", _error)
    def delete(self, project_id: str, member_id: str):
        """Desasigna a la persona del proyecto sin afectar registros históricos"""
        uid, mid = parse_uuid(project_id), parse_uuid(member_id)
        if not uid or not mid:
            return {"error": "validation_error", "message": "UUID invalido"}, 400
        try:
            if not ProjectMemberRepository(get_db()).delete(mid, uid):
                return {"error": "not_found", "message": "Asignación no encontrada"}, 404
            return "", 204
        except Exception:
            return server_error()


@ns_project_members.route("/<string:project_id>/teams")
@ns_project_members.param("project_id", "UUID del Proyecto")
class ProjectTeamList(Resource):
    @ns_project_members.doc("list_project_teams")
    @ns_project_members.response(200, "Subgrupos del proyecto con sus miembros", _team_list_out)
    @ns_project_members.response(400, "UUID inválido", _error)
    @ns_project_members.response(401, "No autenticado", _error)
    @ns_project_members.response(403, "Sin permiso projects:view", _error)
    @ns_project_members.response(404, "Proyecto no encontrado", _error)
    @ns_project_members.response(500, "Error interno del servidor", _error)
    def get(self, project_id: str):
        """Lista los subgrupos "Equipo" del proyecto"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        try:
            db = get_db()
            if not ProjectRepository(db).get_by_id(uid):
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            items = ProjectMemberRepository(db).list_teams(uid)
            return {"items": items, "total": len(items)}, 200
        except Exception:
            return server_error()

    @ns_project_members.doc("create_project_team")
    @ns_project_members.expect(_team_input, validate=False)
    @ns_project_members.response(201, "Subgrupo creado (sin miembros)", _team_out)
    @ns_project_members.response(400, "Nombre vacío", _error)
    @ns_project_members.response(401, "No autenticado", _error)
    @ns_project_members.response(403, "Sin permiso projects:create", _error)
    @ns_project_members.response(404, "Proyecto no encontrado", _error)
    @ns_project_members.response(409, "Nombre duplicado en el proyecto (duplicate_name)", _error)
    @ns_project_members.response(500, "Error interno del servidor", _error)
    def post(self, project_id: str):
        """Crea un subgrupo "Equipo" (puede quedar vacío)"""
        uid = parse_uuid(project_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de proyecto invalido"}, 400
        data = request.get_json(silent=True) or {}
        try:
            db = get_db()
            if not ProjectRepository(db).get_by_id(uid):
                return {"error": "not_found", "message": "Proyecto no encontrado"}, 404
            repo = ProjectMemberRepository(db)
            name = _svc.validate_team_name(uid, data.get("name", ""), members_repo=repo)
            created = repo.create_team(ProjectTeam.create(project_id=uid, name=name))
            return _team_dict(repo, created), 201, {"Location": f"/api/project-teams/{created.id}"}
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns_teams.route("/<string:team_id>")
@ns_teams.param("team_id", "UUID del equipo")
class ProjectTeamDetail(Resource):
    @ns_teams.doc("rename_project_team")
    @ns_teams.expect(_team_input, validate=False)
    @ns_teams.response(200, "Subgrupo renombrado", _team_out)
    @ns_teams.response(400, "Nombre vacío o UUID inválido", _error)
    @ns_teams.response(401, "No autenticado", _error)
    @ns_teams.response(403, "Sin permiso projects:edit", _error)
    @ns_teams.response(404, "Equipo no encontrado", _error)
    @ns_teams.response(409, "Nombre duplicado en el proyecto (duplicate_name)", _error)
    @ns_teams.response(500, "Error interno del servidor", _error)
    def patch(self, team_id: str):
        """Renombra un subgrupo"""
        tid = parse_uuid(team_id)
        if not tid:
            return {"error": "validation_error", "message": "UUID invalido"}, 400
        data = request.get_json(silent=True) or {}
        try:
            db = get_db()
            repo = ProjectMemberRepository(db)
            team = repo.get_team_by_id(tid)
            if not team:
                return {"error": "not_found", "message": "Equipo no encontrado"}, 404
            name = _svc.validate_team_name(team.project_id, data.get("name", ""),
                                           members_repo=repo, exclude_team_id=tid)
            updated = repo.rename_team(tid, name)
            return _team_dict(repo, updated), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()

    @ns_teams.doc("delete_project_team")
    @ns_teams.response(204, "Subgrupo eliminado; sus miembros siguen asignados al proyecto")
    @ns_teams.response(400, "UUID inválido", _error)
    @ns_teams.response(401, "No autenticado", _error)
    @ns_teams.response(403, "Sin permiso projects:deactivate", _error)
    @ns_teams.response(404, "Equipo no encontrado", _error)
    @ns_teams.response(500, "Error interno del servidor", _error)
    def delete(self, team_id: str):
        """Elimina el subgrupo (solo la agrupación, no las asignaciones al proyecto)"""
        tid = parse_uuid(team_id)
        if not tid:
            return {"error": "validation_error", "message": "UUID invalido"}, 400
        try:
            if not ProjectMemberRepository(get_db()).delete_team(tid):
                return {"error": "not_found", "message": "Equipo no encontrado"}, 404
            return "", 204
        except Exception:
            return server_error()


@ns_teams.route("/<string:team_id>/members")
@ns_teams.param("team_id", "UUID del equipo")
class ProjectTeamMembers(Resource):
    @ns_teams.doc("set_project_team_members")
    @ns_teams.expect(_team_members_input, validate=False)
    @ns_teams.response(200, "Conjunto de miembros reemplazado", _team_out)
    @ns_teams.response(400, "Datos inválidos", _error)
    @ns_teams.response(401, "No autenticado", _error)
    @ns_teams.response(403, "Sin permiso projects:edit", _error)
    @ns_teams.response(404, "Equipo no encontrado", _error)
    @ns_teams.response(409, "Algún member_id no es personal del proyecto "
                             "(member_not_in_project)", _error)
    @ns_teams.response(500, "Error interno del servidor", _error)
    def put(self, team_id: str):
        """Reemplaza la lista completa de miembros (patrón resource_skills)"""
        tid = parse_uuid(team_id)
        if not tid:
            return {"error": "validation_error", "message": "UUID invalido"}, 400
        data = request.get_json(silent=True)
        if not data or not isinstance(data.get("member_ids"), list):
            return {"error": "validation_error",
                    "message": "El campo member_ids (lista) es requerido"}, 400
        member_ids = []
        for raw in data["member_ids"]:
            mid = parse_uuid(str(raw))
            if not mid:
                return {"error": "validation_error", "message": f"member_id invalido: {raw}"}, 400
            member_ids.append(mid)
        try:
            db = get_db()
            repo = ProjectMemberRepository(db)
            team = repo.get_team_by_id(tid)
            if not team:
                return {"error": "not_found", "message": "Equipo no encontrado"}, 404
            _svc.validate_team_members(team.project_id, member_ids, members_repo=repo)
            repo.replace_team_members(tid, member_ids)
            return _team_dict(repo, team), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


# ── Enforcement FR-022: JWT + permiso del módulo `projects` por método HTTP ───
from backend.api.middleware.rbac import enforce_module as _enforce

for _cls in (ProjectMemberList, ProjectMemberDetail, ProjectTeamList,
             ProjectTeamDetail, ProjectTeamMembers):
    _cls.method_decorators = [_enforce("projects")]
