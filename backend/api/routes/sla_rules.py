"""Rutas de reglas de SLA por Proyecto + Prioridad (Fase 4, spec 014, contracts/sla-contract.md).

Todas exigen JWT + permiso `sla_rules:manage` (Admin/Coordinador, FR-013). No hay endpoint
DELETE — desactivar (`PATCH {active:false}`) es la única baja soportada (los tickets en curso
referencian `sla_rule_id`).
"""
from flask import request
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.sla_rule import PRIORITIES, SlaRule
from backend.domain.errors import DomainError
from backend.infra.database import get_db
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.sla_rule_repo import SlaRuleRepository

ns = Namespace("sla-rules", description="Reglas de SLA por Proyecto y Prioridad", path="/api/sla-rules")

_error = error_model(ns, "SlaRuleError")

_sla_rule_input = ns.model("SlaRuleInput", {
    "project_id": fields.String(required=True),
    "priority": fields.String(required=True, description="critical | high | medium | low"),
    "contact_minutes": fields.Integer(required=True),
    "execution_minutes": fields.Integer(required=True),
})

_sla_rule_patch_input = ns.model("SlaRulePatchInput", {
    "contact_minutes": fields.Integer(),
    "execution_minutes": fields.Integer(),
    "active": fields.Boolean(),
})

_sla_rule_out = ns.model("SlaRule", {
    "id": fields.String(),
    "project_id": fields.String(),
    "project_name": fields.String(),
    "priority": fields.String(),
    "contact_minutes": fields.Integer(),
    "execution_minutes": fields.Integer(),
    "active": fields.Boolean(),
    "created_at": fields.String(),
})

_sla_rule_list_out = ns.model("SlaRuleList", {
    "items": fields.List(fields.Nested(_sla_rule_out)),
    "total": fields.Integer(),
    "page": fields.Integer(),
    "page_size": fields.Integer(),
})


def _serialize(rule: SlaRule, db) -> dict:
    project = ProjectRepository(db).get_by_id(rule.project_id)
    return {
        "id": str(rule.id),
        "project_id": str(rule.project_id),
        "project_name": project.name if project else None,
        "priority": rule.priority,
        "contact_minutes": rule.contact_minutes,
        "execution_minutes": rule.execution_minutes,
        "active": rule.active,
        "created_at": rule.created_at.isoformat(),
    }


def _validate_minutes(data: dict) -> None:
    for f in ("contact_minutes", "execution_minutes"):
        if f in data and data[f] is not None:
            try:
                if int(data[f]) <= 0:
                    raise DomainError("validation_error", f"'{f}' debe ser un entero > 0", status_code=400)
            except (TypeError, ValueError):
                raise DomainError("validation_error", f"'{f}' debe ser un entero > 0", status_code=400)


@ns.route("")
class SlaRuleList(Resource):
    @ns.doc("list_sla_rules", params={
        "project_id": {"type": "string"},
        "page": {"type": "integer", "default": 1}, "page_size": {"type": "integer", "default": 20},
    })
    @ns.response(200, "Listado de reglas de SLA", _sla_rule_list_out)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso sla_rules:manage", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("sla_rules", "manage")
    def get(self):
        db = get_db()
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        project_id = parse_uuid(request.args.get("project_id") or "") or None
        try:
            items, total = SlaRuleRepository(db).list_paginated(
                page=page, page_size=page_size, project_id=project_id)
            return {"items": [_serialize(r, db) for r in items], "total": total,
                    "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_sla_rule")
    @ns.expect(_sla_rule_input, validate=False)
    @ns.response(201, "Regla creada", _sla_rule_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso sla_rules:manage", _error)
    @ns.response(404, "project_id no existe", _error)
    @ns.response(409, "Ya existe una regla activa para ese (project_id, priority)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("sla_rules", "manage")
    def post(self):
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        for f in ("project_id", "priority", "contact_minutes", "execution_minutes"):
            if data.get(f) is None:
                return {"error": "validation_error", "message": f"El campo '{f}' es requerido"}, 400
        project_id = parse_uuid(data["project_id"])
        if not project_id:
            return {"error": "validation_error", "message": "project_id inválido"}, 400
        priority = data["priority"]
        if priority not in PRIORITIES:
            return {"error": "validation_error",
                    "message": f"priority debe ser una de: {', '.join(PRIORITIES)}"}, 400
        db = get_db()
        try:
            _validate_minutes(data)
            if not ProjectRepository(db).get_by_id(project_id):
                return {"error": "not_found", "message": "El proyecto indicado no existe"}, 404
            repo = SlaRuleRepository(db)
            if repo.exists_active(project_id, priority):
                return {"error": "duplicate_rule",
                        "message": "Ya existe una regla activa para este Proyecto y Prioridad"}, 409
            rule = SlaRule.create(project_id=project_id, priority=priority,
                                  contact_minutes=int(data["contact_minutes"]),
                                  execution_minutes=int(data["execution_minutes"]))
            created = repo.create(rule)
            return _serialize(created, db), 201, {"Location": f"/api/sla-rules/{created.id}"}
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:rule_id>")
@ns.param("rule_id", "UUID de la regla de SLA")
class SlaRuleDetail(Resource):
    @ns.doc("update_sla_rule")
    @ns.expect(_sla_rule_patch_input, validate=False)
    @ns.response(200, "Regla actualizada", _sla_rule_out)
    @ns.response(400, "UUID o datos inválidos", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso sla_rules:manage", _error)
    @ns.response(404, "Regla no encontrada", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("sla_rules", "manage")
    def patch(self, rule_id):
        parsed_id = parse_uuid(rule_id)
        if not parsed_id:
            return {"error": "validation_error", "message": "rule_id inválido"}, 400
        data = request.get_json(silent=True) or {}
        db = get_db()
        repo = SlaRuleRepository(db)
        existing = repo.get_by_id(parsed_id)
        if not existing:
            return {"error": "not_found", "message": "Regla de SLA no encontrada"}, 404
        try:
            _validate_minutes(data)
            existing.contact_minutes = int(data.get("contact_minutes", existing.contact_minutes))
            existing.execution_minutes = int(data.get("execution_minutes", existing.execution_minutes))
            if "active" in data:
                existing.active = bool(data["active"])
            updated = repo.update(existing)
            return _serialize(updated, db), 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
