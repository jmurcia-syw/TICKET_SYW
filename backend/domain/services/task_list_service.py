"""Reglas de negocio de Listas de tareas (spec 009, Nivel 3 de la jerarquía)."""
import uuid

from backend.domain.errors import DomainError


class TaskListValidationError(DomainError):
    default_status_code = 400


_MAX_LIST_NAME_LENGTH = 60


class TaskListService:
    def validate_create(self, project_id: uuid.UUID, name: str, projects_repo, task_lists_repo=None) -> str:
        project = projects_repo.get_by_id(project_id)
        if not project:
            raise TaskListValidationError(
                "not_found", "Proyecto no encontrado", status_code=404)
        clean_name = (name or "").strip()
        if not clean_name:
            raise TaskListValidationError("validation_error", "El campo 'name' es requerido")
        if len(clean_name) > _MAX_LIST_NAME_LENGTH:
            raise TaskListValidationError(
                "validation_error", f"El nombre de la Lista no puede superar {_MAX_LIST_NAME_LENGTH} caracteres")
        if task_lists_repo and task_lists_repo.get_by_project_and_name(project_id, clean_name):
            raise TaskListValidationError(
                "name_duplicate", "Ya existe una Lista con ese nombre en este Proyecto", status_code=409)
        return clean_name

    def validate_update(self, name: str | None, project_id: uuid.UUID | None = None,
                         task_lists_repo=None, task_list_id: uuid.UUID | None = None) -> str | None:
        if name is None:
            return None
        clean_name = name.strip()
        if not clean_name:
            raise TaskListValidationError("validation_error", "El campo 'name' no puede quedar vacío")
        if len(clean_name) > _MAX_LIST_NAME_LENGTH:
            raise TaskListValidationError(
                "validation_error", f"El nombre de la Lista no puede superar {_MAX_LIST_NAME_LENGTH} caracteres")
        if task_lists_repo and project_id:
            existing = task_lists_repo.get_by_project_and_name(project_id, clean_name)
            if existing and existing.id != task_list_id:
                raise TaskListValidationError(
                    "name_duplicate", "Ya existe una Lista con ese nombre en este Proyecto", status_code=409)
        return clean_name
