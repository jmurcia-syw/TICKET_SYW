import uuid
from backend.domain.entities.user import Role
from backend.domain.errors import DomainError


class RoleBusinessError(DomainError):
    pass


class RoleService:
    def validate_role_change(self, user_id: uuid.UUID, new_role: Role, users_repo=None) -> None:
        if new_role == Role.ADMIN:
            return
        if users_repo:
            user = users_repo.get_by_id(user_id)
            if user and user.role == Role.ADMIN:
                admin_count = users_repo.count_active_admins()
                if admin_count <= 1:
                    raise RoleBusinessError("last_admin", "No se puede cambiar el rol del último Admin activo")

    def validate_deactivation(self, user_id: uuid.UUID, users_repo=None) -> None:
        if users_repo:
            user = users_repo.get_by_id(user_id)
            if user and user.role == Role.ADMIN:
                admin_count = users_repo.count_active_admins()
                if admin_count <= 1:
                    raise RoleBusinessError("last_admin", "No se puede desactivar al último Admin activo")
