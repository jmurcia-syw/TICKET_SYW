import uuid
from typing import Optional

from backend.domain.entities.resource import SKILL_TYPES
from backend.domain.errors import DomainError


class SkillBusinessError(DomainError):
    pass


class SkillService:
    def validate_type(self, skill_type: Optional[str]) -> str:
        """`skill_type` es obligatorio: 'funcional' | 'tecnico' (spec 010, FR-013)."""
        if not skill_type or skill_type not in SKILL_TYPES:
            raise SkillBusinessError(
                "validation_error",
                f"El campo skill_type es requerido y debe ser uno de: {', '.join(SKILL_TYPES)}",
                status_code=400)
        return skill_type

    def validate_catalog_refs(self, tool_id: Optional[uuid.UUID],
                              process_id: Optional[uuid.UUID],
                              tools_repo=None, processes_repo=None) -> None:
        """Herramienta/proceso opcionales; si vienen deben existir (FR-014)."""
        if tool_id and tools_repo and not tools_repo.get_by_id(tool_id):
            raise SkillBusinessError("not_found", "Herramienta no encontrada", status_code=404)
        if process_id and processes_repo and not processes_repo.get_by_id(process_id):
            raise SkillBusinessError("not_found", "Proceso no encontrado", status_code=404)

    def validate_delete(self, skill_id: uuid.UUID, resources_repo=None) -> None:
        if resources_repo:
            count = resources_repo.count_active_resources_with_skill(skill_id)
            if count > 0:
                raise SkillBusinessError("skill_in_use", f"El skill está asignado a {count} recurso(s) activo(s)", resource_count=count)
