import uuid


class SkillBusinessError(Exception):
    def __init__(self, code: str, message: str, **extra) -> None:
        self.code = code
        self.message = message
        self.extra = extra
        super().__init__(message)


class SkillService:
    def validate_delete(self, skill_id: uuid.UUID, resources_repo=None) -> None:
        if resources_repo:
            count = resources_repo.count_active_resources_with_skill(skill_id)
            if count > 0:
                raise SkillBusinessError("skill_in_use", f"El skill está asignado a {count} recurso(s) activo(s)", resource_count=count)
