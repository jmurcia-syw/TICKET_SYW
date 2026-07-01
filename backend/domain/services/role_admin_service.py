import uuid
from backend.domain.errors import DomainError


class RoleAdminError(DomainError):
    pass


class RoleAdminService:
    ADMIN_ROLE_NAME = "Admin"

    def validate_deactivation(self, role, users_repo=None) -> None:
        if role.name == self.ADMIN_ROLE_NAME:
            raise RoleAdminError("cannot_deactivate_admin_role", "El rol Admin no se puede desactivar")
        if users_repo:
            count = users_repo.count_active_users_with_role(role.id)
            if count > 0:
                raise RoleAdminError(
                    "role_in_use", f"El rol tiene {count} usuario(s) activo(s) asignado(s)",
                    active_users_count=count,
                )

    def validate_permission_delete(self, permission_id: uuid.UUID, roles_repo=None) -> None:
        if roles_repo:
            count = roles_repo.count_roles_with_permission(permission_id)
            if count > 0:
                raise RoleAdminError(
                    "permission_in_use", f"El permiso está asignado a {count} rol(es)",
                    role_count=count,
                )
