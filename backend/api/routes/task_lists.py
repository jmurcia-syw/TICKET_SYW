"""Listas de tareas dentro de un Proyecto (spec 009, Nivel 3 de la jerarquía).

Mismo patrón que `client_contacts.py`: CRUD simple anidado bajo su padre jerárquico, protegido
por el permiso ya existente `tickets:create` (sin permiso nuevo) — mismo permiso que ya tiene
cualquier rol que puede crear una Tarea (Resolutor incluido), ya que organizar Listas es parte
del mismo flujo de trabajo, no una acción de edición de campos (`tickets:edit`, reservado a
roles de gestión)."""
import uuid

from flask import request
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.domain.entities.task_list import TaskList
from backend.domain.errors import DomainError
from backend.domain.services.task_list_service import TaskListService
from backend.infra.database import get_db
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.task_list_repo import TaskListRepository

# Dos namespaces con prefijos distintos (mismo criterio que separar rutas anidadas bajo
# `/api/projects` de rutas propias `/api/task-lists` — flask-restx exige un `path` fijo por
# Namespace, no se pueden mezclar dos prefijos absolutos en uno solo).
ns_project_lists = Namespace("project-task-lists", description="Listas de tareas de un Proyecto",
                             path="/api/projects")
ns = Namespace("task-lists", description="Listas de tareas (edición directa)", path="/api/task-lists")

_svc = TaskListService()

_error = error_model(ns, "TaskListError")

_task_list_input = ns.model("TaskListInput", {
    "name": fields.String(required=True),
})

_task_list_update_input = ns.model("TaskListUpdateInput", {
    "name": fields.String(),
    "position": fields.Integer(),
})

_task_list_out = ns.model("TaskList", {
    "id": fields.String(description="UUID de la Lista"),
    "project_id": fields.String(description="UUID del Proyecto"),
    "name": fields.String(),
    "position": fields.Integer(),
    "task_count": fields.Integer(description="Tareas de Nivel 4 asociadas (sin contar Subtareas)"),
})

_task_list_list_out = ns.model("TaskListList", {
    "items": fields.List(fields.Nested(_task_list_out)),
})


@ns_project_lists.route("/<string:project_id>/task-lists")
@ns_project_lists.param("project_id", "UUID del Proyecto")
class ProjectTaskLists(Resource):
    @ns_project_lists.doc("list_task_lists")
    @ns_project_lists.response(200, "Listas del Proyecto, ordenadas por posición", _task_list_list_out)
    @ns_project_lists.response(400, "UUID inválido", _error)
    @ns_project_lists.response(401, "No autenticado", _error)
    @ns_project_lists.response(403, "Sin permiso tickets:create", _error)
    @ns_project_lists.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "create")
    def get(self, project_id: str):
        pid = parse_uuid(project_id)
        if not pid:
            return {"error": "validation_error", "message": "ID de proyecto inválido"}, 400
        try:
            db = get_db()
            items = TaskListRepository(db).list_by_project(pid)
            return {"items": items}, 200
        except Exception:
            return server_error()

    @ns_project_lists.doc("create_task_list")
    @ns_project_lists.expect(_task_list_input, validate=False)
    @ns_project_lists.response(201, "Lista creada", _task_list_out)
    @ns_project_lists.response(400, "El campo 'name' es requerido", _error)
    @ns_project_lists.response(401, "No autenticado", _error)
    @ns_project_lists.response(403, "Sin permiso tickets:create", _error)
    @ns_project_lists.response(404, "Proyecto no encontrado", _error)
    @ns_project_lists.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "create")
    def post(self, project_id: str):
        pid = parse_uuid(project_id)
        if not pid:
            return {"error": "validation_error", "message": "ID de proyecto inválido"}, 400
        data = request.get_json(silent=True) or {}
        try:
            db = get_db()
            repo = TaskListRepository(db)
            name = _svc.validate_create(pid, data.get("name", ""), ProjectRepository(db), task_lists_repo=repo)
            task_list = TaskList(
                id=uuid.uuid4(), project_id=pid, name=name,
                position=repo.next_position(pid),
            )
            created = repo.create(task_list)
            return {
                "id": str(created.id), "project_id": str(created.project_id),
                "name": created.name, "position": created.position, "task_count": 0,
            }, 201, {"Location": f"/api/task-lists/{created.id}"}
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:task_list_id>")
@ns.param("task_list_id", "UUID de la Lista")
class TaskListDetail(Resource):
    @ns.doc("update_task_list")
    @ns.expect(_task_list_update_input, validate=False)
    @ns.response(200, "Lista actualizada", _task_list_out)
    @ns.response(400, "UUID inválido o 'name' vacío", _error)
    @ns.response(401, "No autenticado", _error)
    @ns.response(403, "Sin permiso tickets:create", _error)
    @ns.response(404, "Lista no encontrada", _error)
    @ns.response(500, "Error interno del servidor", _error)
    @require_permission("tickets", "create")
    def patch(self, task_list_id: str):
        tlid = parse_uuid(task_list_id)
        if not tlid:
            return {"error": "validation_error", "message": "ID de lista inválido"}, 400
        data = request.get_json(silent=True) or {}
        try:
            db = get_db()
            repo = TaskListRepository(db)
            if "name" in data:
                existing_list = repo.get_by_id(tlid)
                if not existing_list:
                    return {"error": "not_found", "message": "Lista no encontrada"}, 404
                fields_to_set = {"name": _svc.validate_update(
                    data.get("name"), project_id=existing_list.project_id,
                    task_lists_repo=repo, task_list_id=tlid,
                )}
            else:
                fields_to_set = {}
            if "position" in data:
                fields_to_set["position"] = int(data["position"])
            updated = repo.update(tlid, **fields_to_set)
            if not updated:
                return {"error": "not_found", "message": "Lista no encontrada"}, 404
            counts = repo.list_by_project(updated.project_id)
            task_count = next((c["task_count"] for c in counts if c["id"] == str(updated.id)), 0)
            return {
                "id": str(updated.id), "project_id": str(updated.project_id),
                "name": updated.name, "position": updated.position, "task_count": task_count,
            }, 200
        except DomainError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
