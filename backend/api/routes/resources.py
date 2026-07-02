from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.resource_repo import ResourceRepository, SkillRepository
from backend.infra.database import get_db
from backend.domain.entities.resource import Resource as ResourceEntity, Skill
from backend.domain.services.skill_service import SkillService, SkillBusinessError
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("resources", description="Gestión de recursos y skills", path="/api")
_skill_svc = SkillService()

# ── Models ────────────────────────────────────────────────────────────────────

_error = error_model(ns, "ResourceError")

_skill_out = ns.model("Skill", {
    "id": fields.String(description="UUID del skill"),
    "code": fields.String(description="Código único (UPPER_SNAKE_CASE)", example="JDE_GL"),
    "label": fields.String(description="Nombre descriptivo", example="JD Edwards General Ledger"),
    "active": fields.Boolean(description="Estado activo"),
})

_skill_list_out = ns.model("SkillList", {
    "items": fields.List(fields.Nested(_skill_out)),
    "total": fields.Integer(description="Total de skills"),
})

_skill_input = ns.model("SkillInput", {
    "code": fields.String(required=True, description="Código único (UPPER_SNAKE_CASE)", example="ORACLE_FUSION"),
    "label": fields.String(required=True, description="Nombre descriptivo", example="Oracle Fusion Cloud"),
})

_skill_ref = ns.model("SkillRef", {
    "id": fields.String(description="UUID del skill"),
    "code": fields.String(description="Código del skill"),
    "label": fields.String(description="Nombre descriptivo"),
})

_resource_out = ns.model("ResourceRecord", {
    "id": fields.String(description="UUID del recurso"),
    "user_id": fields.String(description="UUID del usuario del sistema vinculado (opcional)"),
    "full_name": fields.String(description="Nombre completo del colaborador"),
    "email": fields.String(description="Email corporativo @sywork.net"),
    "active": fields.Boolean(description="Estado activo"),
    "notes": fields.String(description="Notas internas"),
    "skills": fields.List(fields.Nested(_skill_ref), description="Skills asignados"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_resource_list_out = ns.model("ResourceList", {
    "items": fields.List(fields.Nested(_resource_out)),
    "total": fields.Integer(description="Total de recursos"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_resource_input = ns.model("ResourceInput", {
    "full_name": fields.String(required=True, description="Nombre completo", example="Ana López"),
    "email": fields.String(required=True, description="Email @sywork.net", example="ana.lopez@sywork.net"),
    "user_id": fields.String(description="UUID del usuario del sistema a vincular (opcional)"),
    "notes": fields.String(description="Notas internas"),
    "skill_ids": fields.List(fields.String, description="Lista de UUIDs de skills", example=[]),
})

_resource_update = ns.model("ResourceUpdate", {
    "full_name": fields.String(description="Nuevo nombre completo"),
    "notes": fields.String(description="Notas internas"),
})

_skills_update = ns.model("ResourceSkillsUpdate", {
    "skill_ids": fields.List(
        fields.String,
        required=True,
        description="Lista completa de UUIDs de skills (reemplaza los actuales)",
    ),
})

_status_result = ns.model("ResourceStatusResult", {
    "id": fields.String(description="UUID del recurso"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})


def _resource_to_dict(resource) -> dict:
    return {
        "id": str(resource.id),
        "user_id": str(resource.user_id) if resource.user_id else None,
        "full_name": resource.full_name,
        "email": resource.email,
        "active": resource.active,
        "notes": resource.notes,
        "skills": [{"id": str(s.id), "code": s.code, "label": s.label} for s in (resource.skills or [])],
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
    }


# ── Skills endpoints ──────────────────────────────────────────────────────────

@ns.route("/skills")
class SkillList(Resource):
    @ns.doc(
        "list_skills",
        params={
            "active": {
                "description": "Filtrar por estado: true, false, all (default: all)",
                "type": "string",
                "default": "all",
            },
        },
    )
    @ns.response(200, "Listado de skills", _skill_list_out)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar todos los skills disponibles (códigos de habilidad parametrizados)"""
        from flask import request
        active_param = request.args.get("active", "all")
        active = None if active_param == "all" else active_param.lower() == "true"
        try:
            db = next(get_db())
            skills = SkillRepository(db).list_all(active=active)
            return {
                "items": [{"id": str(s.id), "code": s.code, "label": s.label, "active": s.active} for s in skills],
                "total": len(skills),
            }, 200
        except Exception:
            return server_error()

    @ns.doc("create_skill")
    @ns.expect(_skill_input, validate=False)
    @ns.response(201, "Skill creado", _skill_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(409, "Código de skill duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un nuevo skill. El código se normaliza a UPPER_SNAKE_CASE automáticamente."""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        code = data.get("code", "").strip().upper()
        label = data.get("label", "").strip()
        if not code:
            return {"error": "validation_error", "message": "El campo 'code' es requerido"}, 400
        if not label:
            return {"error": "validation_error", "message": "El campo 'label' es requerido"}, 400
        try:
            db = next(get_db())
            repo = SkillRepository(db)
            if repo.get_by_code(code):
                return {"error": "code_duplicate", "message": f"Ya existe un skill con codigo {code}"}, 409
            skill = Skill.create(code=code, label=label)
            created = repo.create(skill)
            return (
                {"id": str(created.id), "code": created.code, "label": created.label, "active": created.active},
                201,
                {"Location": f"/api/skills/{created.id}"},
            )
        except Exception:
            return server_error()


@ns.route("/skills/<string:skill_id>")
@ns.param("skill_id", "UUID del skill")
class SkillDetail(Resource):
    @ns.doc("delete_skill")
    @ns.response(204, "Skill eliminado correctamente")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(409, "No se puede eliminar: skill asignado a recursos", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def delete(self, skill_id: str):
        """Eliminar un skill. Retorna 409 si está asignado a algún recurso."""
        uid = parse_uuid(skill_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de skill invalido"}, 400
        try:
            db = next(get_db())
            skill_repo = SkillRepository(db)
            _skill_svc.validate_delete(uid, resources_repo=skill_repo)
            skill_repo.delete(uid)
            return "", 204
        except SkillBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


# ── Resources endpoints ───────────────────────────────────────────────────────

@ns.route("/resources")
class ResourceList(Resource):
    @ns.doc(
        "list_resources",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "search": {"description": "Búsqueda por nombre o email", "type": "string"},
            "skill_code": {"description": "Filtrar por código de skill (ej: JDE_GL)", "type": "string"},
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(200, "Listado de recursos con sus skills", _resource_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar recursos/colaboradores con sus skills asignados"""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        search = request.args.get("search", "").strip() or None
        skill_code = request.args.get("skill_code", "").strip() or None
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        try:
            db = next(get_db())
            items, total = ResourceRepository(db).list_paginated(
                page=page, page_size=page_size, search=search, skill_code=skill_code, active=active,
            )
            return {"items": [_resource_to_dict(r) for r in items], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_resource")
    @ns.expect(_resource_input, validate=False)
    @ns.response(201, "Recurso creado", _resource_out)
    @ns.response(400, "Datos inválidos o email fuera de dominio @sywork.net", _error)
    @ns.response(409, "Email duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un nuevo recurso/colaborador. El email debe ser del dominio @sywork.net."""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        full_name = data.get("full_name", "").strip()
        email = data.get("email", "").strip().lower()
        if not full_name:
            return {"error": "validation_error", "message": "El campo 'full_name' es requerido"}, 400
        if not email:
            return {"error": "validation_error", "message": "El campo 'email' es requerido"}, 400
        if not email.endswith("@sywork.net"):
            return {"error": "invalid_email_domain", "message": "El email debe ser del dominio @sywork.net"}, 400
        try:
            db = next(get_db())
            repo = ResourceRepository(db)
            if repo.get_by_email(email):
                return {"error": "email_duplicate", "message": f"Ya existe un recurso con el email {email}"}, 409
            skill_ids = [parse_uuid(sid) for sid in data.get("skill_ids", [])]
            skill_ids = [s for s in skill_ids if s]
            skill_repo = SkillRepository(db)
            skill_entities = [s for s in [skill_repo.get_by_id(sid) for sid in skill_ids] if s]
            resource = ResourceEntity.create(
                full_name=full_name,
                email=email,
                user_id=parse_uuid(data["user_id"]) if data.get("user_id") else None,
                notes=data.get("notes"),
                skills=skill_entities,
            )
            created = repo.create(resource)
            return _resource_to_dict(created), 201, {"Location": f"/api/resources/{created.id}"}
        except Exception:
            return server_error()


@ns.route("/resources/<string:resource_id>")
@ns.param("resource_id", "UUID del recurso")
class ResourceDetail(Resource):
    @ns.doc("get_resource")
    @ns.response(200, "Detalle del recurso", _resource_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, resource_id: str):
        """Obtener detalle de un recurso incluyendo sus skills"""
        uid = parse_uuid(resource_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
        try:
            db = next(get_db())
            resource = ResourceRepository(db).get_by_id(uid)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            return _resource_to_dict(resource), 200
        except Exception:
            return server_error()

    @ns.doc("update_resource")
    @ns.expect(_resource_update, validate=False)
    @ns.response(200, "Recurso actualizado", _resource_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, resource_id: str):
        """Actualizar campos de un recurso (PATCH parcial). Para skills usar /skills, para estado usar /activate o /deactivate."""
        from flask import request
        uid = parse_uuid(resource_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = next(get_db())
            repo = ResourceRepository(db)
            resource = repo.get_by_id(uid)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            allowed = {k: v for k, v in data.items() if k in ("full_name", "notes")}
            updated = repo.update(uid, **allowed)
            return _resource_to_dict(updated), 200
        except Exception:
            return server_error()


@ns.route("/resources/<string:resource_id>/skills")
@ns.param("resource_id", "UUID del recurso")
class ResourceSkills(Resource):
    @ns.doc("update_resource_skills")
    @ns.expect(_skills_update, validate=False)
    @ns.response(200, "Skills actualizados (reemplaza lista completa)", _resource_out)
    @ns.response(400, "UUID inválido o cuerpo incorrecto", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, resource_id: str):
        """Reemplazar todos los skills de un recurso (operación de reemplazo total, no incremental)"""
        from flask import request
        uid = parse_uuid(resource_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
        data = request.get_json(silent=True) or {}
        skill_ids = [parse_uuid(sid) for sid in data.get("skill_ids", [])]
        skill_ids = [s for s in skill_ids if s]
        try:
            db = next(get_db())
            resource = ResourceRepository(db).update_skills(uid, skill_ids)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            return _resource_to_dict(resource), 200
        except Exception:
            return server_error()


@ns.route("/resources/<string:resource_id>/deactivate")
@ns.param("resource_id", "UUID del recurso")
class ResourceDeactivate(Resource):
    @ns.doc("deactivate_resource")
    @ns.response(200, "Recurso desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, resource_id: str):
        """Desactivar un recurso/colaborador"""
        uid = parse_uuid(resource_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
        try:
            db = next(get_db())
            resource = ResourceRepository(db).deactivate(uid)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            return {"id": resource_id, "active": False}, 200
        except Exception:
            return server_error()


@ns.route("/resources/<string:resource_id>/activate")
@ns.param("resource_id", "UUID del recurso")
class ResourceActivate(Resource):
    @ns.doc("activate_resource")
    @ns.response(200, "Recurso activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(409, "El recurso ya está activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, resource_id: str):
        """Activar un recurso previamente desactivado"""
        uid = parse_uuid(resource_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
        try:
            db = next(get_db())
            repo = ResourceRepository(db)
            resource = repo.get_by_id(uid)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            if resource.active:
                return {"error": "already_active", "message": "El recurso ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": resource_id, "active": True}, 200
        except Exception:
            return server_error()
