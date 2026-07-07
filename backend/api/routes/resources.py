from datetime import date

from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.resource_repo import ResourceRepository, SkillRepository, CompensationRepository
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.database import get_db
from backend.domain.entities.resource import Resource as ResourceEntity, Skill
from backend.domain.services.skill_service import SkillService, SkillBusinessError
from backend.domain.services.compensation_service import CompensationService, CompensationBusinessError
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("resources", description="Gestión de recursos y skills", path="/api")
_skill_svc = SkillService()
_comp_svc = CompensationService()

# Campos de texto del perfil extendido SDD V3 (FR-031) editables via POST/PATCH
_PROFILE_TEXT_FIELDS = (
    "identification", "nationality", "marital_status", "contract_type",
    "calendar_country", "education_level", "specialty", "seniority",
    "certifications", "team",
)

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
    "identification": fields.String(description="Número de identificación"),
    "nationality": fields.String(description="Nacionalidad"),
    "birth_date": fields.String(description="Fecha de nacimiento (YYYY-MM-DD)"),
    "marital_status": fields.String(description="Estado civil"),
    "contract_type": fields.String(description="Tipo de contrato"),
    "calendar_country": fields.String(description="País base del calendario de trabajo"),
    "education_level": fields.String(description="Nivel de estudios"),
    "specialty": fields.String(description="Especialidad (Desarrollador, Funcional, Infraestructura...)"),
    "seniority": fields.String(description="Seniority (Junior, Staff, Senior)"),
    "certifications": fields.String(description="Certificaciones"),
    "team": fields.String(description="Equipo al que pertenece"),
    "manager_id": fields.String(description="UUID del recurso jefe directo"),
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
    "identification": fields.String(description="Número de identificación"),
    "nationality": fields.String(description="Nacionalidad"),
    "birth_date": fields.String(description="Fecha de nacimiento (YYYY-MM-DD)"),
    "marital_status": fields.String(description="Estado civil"),
    "contract_type": fields.String(description="Tipo de contrato"),
    "calendar_country": fields.String(description="País base del calendario"),
    "education_level": fields.String(description="Nivel de estudios"),
    "specialty": fields.String(description="Especialidad"),
    "seniority": fields.String(description="Seniority"),
    "certifications": fields.String(description="Certificaciones"),
    "team": fields.String(description="Equipo"),
    "manager_id": fields.String(description="UUID del recurso jefe directo"),
    "skill_ids": fields.List(fields.String, description="Lista de UUIDs de skills", example=[]),
})

_resource_update = ns.model("ResourceUpdate", {
    "full_name": fields.String(description="Nuevo nombre completo"),
    "user_id": fields.String(description="Vincular (o null para desvincular) una cuenta de acceso existente sin cuenta propia"),
    "notes": fields.String(description="Notas internas"),
    "identification": fields.String(description="Número de identificación"),
    "nationality": fields.String(description="Nacionalidad"),
    "birth_date": fields.String(description="Fecha de nacimiento (YYYY-MM-DD)"),
    "marital_status": fields.String(description="Estado civil"),
    "contract_type": fields.String(description="Tipo de contrato"),
    "calendar_country": fields.String(description="País base del calendario"),
    "education_level": fields.String(description="Nivel de estudios"),
    "specialty": fields.String(description="Especialidad"),
    "seniority": fields.String(description="Seniority"),
    "certifications": fields.String(description="Certificaciones"),
    "team": fields.String(description="Equipo"),
    "manager_id": fields.String(description="UUID del recurso jefe directo (null para quitar)"),
})

_compensation_out = ns.model("ResourceCompensation", {
    "resource_id": fields.String(description="UUID del recurso"),
    "base_salary": fields.Float(description="Salario base"),
    "total_salary": fields.Float(description="Salario total con beneficios"),
    "overhead": fields.Float(description="Costos adicionales / overhead"),
    "hourly_cost": fields.Float(description="Costo hora calculado por el sistema (solo lectura)"),
    "currency": fields.String(description="Moneda"),
    "updated_at": fields.String(description="Última modificación ISO-8601"),
})

_compensation_input = ns.model("ResourceCompensationInput", {
    "base_salary": fields.Float(description="Salario base"),
    "total_salary": fields.Float(description="Salario total con beneficios"),
    "overhead": fields.Float(description="Costos adicionales / overhead"),
    "currency": fields.String(description="Moneda (default USD)", example="USD"),
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
        "identification": resource.identification,
        "nationality": resource.nationality,
        "birth_date": resource.birth_date.isoformat() if resource.birth_date else None,
        "marital_status": resource.marital_status,
        "contract_type": resource.contract_type,
        "calendar_country": resource.calendar_country,
        "education_level": resource.education_level,
        "specialty": resource.specialty,
        "seniority": resource.seniority,
        "certifications": resource.certifications,
        "team": resource.team,
        "manager_id": str(resource.manager_id) if resource.manager_id else None,
        "skills": [{"id": str(s.id), "code": s.code, "label": s.label} for s in (resource.skills or [])],
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
    }


def _parse_profile_fields(data: dict, repo, resource_id=None) -> tuple[dict, tuple[str, int] | None]:
    """Extrae los campos de perfil extendido (FR-031). Devuelve (valores, (mensaje, status) | None)."""
    values: dict = {}
    for f in _PROFILE_TEXT_FIELDS:
        if f in data:
            values[f] = data[f] or None
    if "birth_date" in data:
        if data["birth_date"]:
            try:
                values["birth_date"] = date.fromisoformat(data["birth_date"])
            except ValueError:
                return {}, ("birth_date debe ser YYYY-MM-DD", 400)
        else:
            values["birth_date"] = None
    if "manager_id" in data:
        if data["manager_id"]:
            manager_id = parse_uuid(data["manager_id"])
            if not manager_id:
                return {}, ("manager_id invalido", 400)
            if resource_id and manager_id == resource_id:
                return {}, ("Un recurso no puede ser su propio jefe", 400)
            manager = repo.get_by_id(manager_id)
            if not manager:
                return {}, ("El jefe indicado no existe", 404)
            if not manager.active:
                return {}, ("El jefe indicado debe ser un recurso activo", 400)
            values["manager_id"] = manager_id
        else:
            values["manager_id"] = None
    return values, None


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
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.response(200, "Listado de skills", _skill_list_out)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar todos los skills disponibles (códigos de habilidad parametrizados)"""
        from flask import request
        active_param = request.args.get("active", "all")
        active = None if active_param == "all" else active_param.lower() == "true"
        try:
            db = get_db()
            skills = SkillRepository(db).list_all(active=active)
            return {
                "items": [{"id": str(s.id), "code": s.code, "label": s.label, "active": s.active} for s in skills],
                "total": len(skills),
            }, 200
        except Exception:
            return server_error()

    @ns.doc("create_skill")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
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
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
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
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
            items, total = ResourceRepository(db).list_paginated(
                page=page, page_size=page_size, search=search, skill_code=skill_code, active=active,
            )
            return {"items": [_resource_to_dict(r) for r in items], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_resource")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
            repo = ResourceRepository(db)
            if repo.get_by_email(email):
                return {"error": "email_duplicate", "message": f"Ya existe un recurso con el email {email}"}, 409
            skill_ids = [parse_uuid(sid) for sid in data.get("skill_ids", [])]
            skill_ids = [s for s in skill_ids if s]
            skill_repo = SkillRepository(db)
            skill_entities = [s for s in [skill_repo.get_by_id(sid) for sid in skill_ids] if s]
            profile, profile_error = _parse_profile_fields(data, repo)
            if profile_error:
                message, status = profile_error
                return {"error": "validation_error" if status == 400 else "not_found", "message": message}, status
            resource = ResourceEntity.create(
                full_name=full_name,
                email=email,
                user_id=parse_uuid(data["user_id"]) if data.get("user_id") else None,
                notes=data.get("notes"),
                skills=skill_entities,
                **profile,
            )
            created = repo.create(resource)
            return _resource_to_dict(created), 201, {"Location": f"/api/resources/{created.id}"}
        except Exception:
            return server_error()


@ns.route("/resources/me")
class ResourceMe(Resource):
    @ns.doc("get_my_resource", security="Bearer")
    @ns.response(200, "Recurso vinculado a la cuenta autenticada", _resource_out)
    @ns.response(401, "No autenticado", _error)
    @ns.response(404, "La cuenta autenticada no tiene un recurso vinculado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Recurso vinculado al usuario autenticado (autoservicio "Mi Perfil").

        Sin gate de permiso de módulo a propósito: cualquier cuenta activa puede ver
        su propio perfil, independientemente de si tiene `resources:view`."""
        from flask import g
        from backend.api.middleware.auth import jwt_required_active

        @jwt_required_active
        def _inner():
            try:
                db = get_db()
                resource = ResourceRepository(db).get_by_user_id(g.current_user.id)
                if not resource:
                    return {"error": "not_found", "message": "Tu cuenta no tiene un perfil de recurso asociado"}, 404
                return _resource_to_dict(resource), 200
            except Exception:
                return server_error()

        try:
            return _inner()
        except Exception:
            # Token ausente/invalido: flask-restx interceptaria la excepcion de
            # flask-jwt-extended como 500; se mapea explicitamente a 401 (FR-023)
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401


@ns.route("/resources/<string:resource_id>")
@ns.param("resource_id", "UUID del recurso")
class ResourceDetail(Resource):
    @ns.doc("get_resource")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
            resource = ResourceRepository(db).get_by_id(uid)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            return _resource_to_dict(resource), 200
        except Exception:
            return server_error()

    @ns.doc("update_resource")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_resource_update, validate=False)
    @ns.response(200, "Recurso actualizado", _resource_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Recurso o usuario a vincular no encontrado", _error)
    @ns.response(409, "El usuario indicado ya está vinculado a otro recurso", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, resource_id: str):
        """Actualizar campos de un recurso (PATCH parcial). Para skills usar /skills, para estado usar /activate o /deactivate.

        `user_id` permite vincular (o, con `null`, desvincular) una cuenta de acceso
        existente a un recurso que aún no tiene una — el caso inverso de crear el recurso
        ya vinculado en `POST /resources`."""
        from flask import request
        uid = parse_uuid(resource_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = get_db()
            repo = ResourceRepository(db)
            resource = repo.get_by_id(uid)
            if not resource:
                return {"error": "not_found", "message": "Recurso no encontrado"}, 404
            allowed = {k: v for k, v in data.items() if k in ("full_name", "notes")}
            if "user_id" in data:
                if data["user_id"]:
                    new_user_id = parse_uuid(data["user_id"])
                    if not new_user_id:
                        return {"error": "validation_error", "message": "user_id invalido"}, 400
                    if not UserRepository(db).get_by_id(new_user_id):
                        return {"error": "not_found", "message": "Usuario no encontrado"}, 404
                    linked_to = repo.get_by_user_id(new_user_id)
                    if linked_to and linked_to.id != uid:
                        return {"error": "user_already_linked",
                                "message": f"Ese usuario ya está vinculado al recurso '{linked_to.full_name}'"}, 409
                    allowed["user_id"] = new_user_id
                else:
                    allowed["user_id"] = None
            profile, profile_error = _parse_profile_fields(data, repo, resource_id=uid)
            if profile_error:
                message, status = profile_error
                return {"error": "validation_error" if status == 400 else "not_found", "message": message}, status
            allowed.update(profile)
            updated = repo.update(uid, **allowed)
            return _resource_to_dict(updated), 200
        except Exception:
            return server_error()


@ns.route("/resources/<string:resource_id>/skills")
@ns.param("resource_id", "UUID del recurso")
class ResourceSkills(Resource):
    @ns.doc("update_resource_skills")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
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
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
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
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
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
            db = get_db()
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


# ── Compensación protegida (FR-032/FR-033, SDD V3) ───────────────────────────
# A diferencia del resto de rutas de maestros (enforcement diferido, FR-017),
# esta ruta exige JWT + permiso `compensation` porque es dato sensible (FR-033),
# igual que los campos VPN de clientes.

def _user_has_compensation_permission(db, user, action: str) -> bool:
    from backend.infra.repositories.role_repo import RoleRepository
    permissions = RoleRepository(db).list_permissions_for_role(user.role.id)
    return any(p.module == "compensation" and p.action == action for p in permissions)


def _compensation_to_dict(comp) -> dict:
    return {
        "resource_id": str(comp.resource_id),
        "base_salary": comp.base_salary,
        "total_salary": comp.total_salary,
        "overhead": comp.overhead,
        "hourly_cost": comp.hourly_cost,
        "currency": comp.currency,
        "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
    }


@ns.route("/resources/<string:resource_id>/compensation")
@ns.param("resource_id", "UUID del recurso")
class ResourceCompensationRoute(Resource):
    @ns.doc("get_resource_compensation", security="Bearer")
    @ns.response(200, "Compensación del recurso", _compensation_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso compensation:view", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, resource_id: str):
        """Obtener el área protegida de compensación (requiere permiso compensation:view)"""
        from backend.api.middleware.auth import jwt_required_active

        @jwt_required_active
        def _inner():
            from flask import g
            uid = parse_uuid(resource_id)
            if not uid:
                return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
            try:
                db = get_db()
                if not _user_has_compensation_permission(db, g.current_user, "view"):
                    return {"error": "forbidden", "message": "Acceso denegado"}, 403
                if not ResourceRepository(db).get_by_id(uid):
                    return {"error": "not_found", "message": "Recurso no encontrado"}, 404
                comp = CompensationRepository(db).get(uid)
                if not comp:
                    return {"error": "not_found", "message": "El recurso no tiene compensación registrada"}, 404
                return _compensation_to_dict(comp), 200
            except Exception:
                return server_error()

        try:
            return _inner()
        except Exception:
            # Token ausente/invalido: flask-restx interceptaria la excepcion de
            # flask-jwt-extended como 500; se mapea explicitamente a 401 (FR-023)
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401

    @ns.doc("put_resource_compensation", security="Bearer")
    @ns.expect(_compensation_input, validate=False)
    @ns.response(200, "Compensación guardada (upsert)", _compensation_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso compensation:edit", _error)
    @ns.response(404, "Recurso no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def put(self, resource_id: str):
        """Crear/actualizar la compensación. El costo hora lo calcula el backend (FR-032)."""
        from backend.api.middleware.auth import jwt_required_active

        @jwt_required_active
        def _inner():
            from flask import g, request
            uid = parse_uuid(resource_id)
            if not uid:
                return {"error": "validation_error", "message": "ID de recurso invalido"}, 400
            data = request.get_json(silent=True)
            if data is None:
                return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
            try:
                db = get_db()
                if not _user_has_compensation_permission(db, g.current_user, "edit"):
                    return {"error": "forbidden", "message": "Acceso denegado"}, 403
                if not ResourceRepository(db).get_by_id(uid):
                    return {"error": "not_found", "message": "Recurso no encontrado"}, 404

                def _num(field):
                    value = data.get(field)
                    if value is None:
                        return None
                    return float(value)

                try:
                    base_salary, total_salary, overhead = _num("base_salary"), _num("total_salary"), _num("overhead")
                except (TypeError, ValueError):
                    return {"error": "validation_error", "message": "Los montos deben ser numéricos"}, 400
                comp = _comp_svc.build(
                    resource_id=uid, base_salary=base_salary, total_salary=total_salary,
                    overhead=overhead, currency=data.get("currency") or "USD",
                )
                saved = CompensationRepository(db).upsert(comp)
                return _compensation_to_dict(saved), 200
            except CompensationBusinessError as e:
                return {"error": e.code, "message": e.message, **e.extra}, e.status_code
            except Exception:
                return server_error()

        try:
            return _inner()
        except Exception:
            # Token ausente/invalido: flask-restx interceptaria la excepcion de
            # flask-jwt-extended como 500; se mapea explicitamente a 401 (FR-023)
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401


# ── Enforcement FR-022 (spec 002): JWT + permiso por módulo/acción ─────────────
# La ruta de compensación NO se toca: ya aplica su propio control (compensation:view/edit).
from backend.api.middleware.rbac import enforce_module as _enforce

for _cls in (SkillList, SkillDetail):
    _cls.method_decorators = [_enforce("skills")]
for _cls in (ResourceList, ResourceSkills, ResourceDeactivate, ResourceActivate):
    _cls.method_decorators = [_enforce("resources")]
# FR-012: un Resolutor sin resources:edit puede editar SU propio perfil
ResourceDetail.method_decorators = [_enforce("resources", allow_own_resource_edit=True)]
