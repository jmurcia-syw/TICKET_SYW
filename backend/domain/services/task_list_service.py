"""Reglas de negocio de Listas de tareas (spec 009, Nivel 3 de la jerarquía)."""
import uuid

from backend.domain.errors import DomainError


class TaskListValidationError(DomainError):
    default_status_code = 400


class TaskListService:
    def validate_create(self, project_id: uuid.UUID, name: str, projects_repo) -> str:
        project = projects_repo.get_by_id(project_id)
        if not project:
            raise TaskListValidationError(
                "not_found", "Proyecto no encontrado", status_code=404)
        clean_name = (name or "").strip()
        if not clean_name:
            raise TaskListValidationError("validation_error", "El campo 'name' es requerido")
        return clean_name

    def validate_update(self, name: str | None) -> str | None:
        if name is None:
            return None
        clean_name = name.strip()
        if not clean_name:
            raise TaskListValidationError("validation_error", "El campo 'name' no puede quedar vacío")
        return clean_name
