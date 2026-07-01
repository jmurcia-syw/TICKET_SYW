import uuid
from backend.domain.errors import DomainError


class RoleBusinessError(DomainError):
    pass


class RoleService:
    ADMIN_ROLE_NAME = "Admin"

    def validate_role_change(self, user_id: uuid.UUID, new_role_name: str, users_repo=None) -> None:
        if new_role_name == self.ADMIN_ROLE_NAME:
            return
        if users_repo:
            user = users_repo.get_by_id(user_id)
            if user and user.role.name == self.ADMIN_ROLE_NAME:
                admin_count = users_repo.count_active_admins()
                if admin_count <= 1:
                    raise RoleBusinessError("last_admin", "No se puede cambiar el rol del último Admin activo")

    def validate_deactivation(self, user_id: uuid.UUID, users_repo=None) -> None:
        if users_repo:
            user = users_repo.get_by_id(user_id)
            if user and user.role.name == self.ADMIN_ROLE_NAME:
                admin_count = users_repo.count_active_admins()
                if admin_count <= 1:
                    raise RoleBusinessError("last_admin", "No se puede desactivar al último Admin activo")
