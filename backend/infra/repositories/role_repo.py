import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.infra.models.role_model import RoleModel, PermissionModel, role_permissions_table
from backend.infra.models.user_model import UserModel
from backend.domain.entities.role import Role, Permission


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        model = self._db.get(RoleModel, role_id)
        return model.to_entity() if model else None

    def get_by_name(self, name: str) -> Optional[Role]:
        model = self._db.query(RoleModel).filter(RoleModel.name == name).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, active: bool | None = None) -> tuple[list[Role], int]:
        q = self._db.query(RoleModel)
        if active is not None:
            q = q.filter(RoleModel.active == active)
        total = q.count()
        models = q.order_by(RoleModel.name).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def list_permissions_for_role(self, role_id: uuid.UUID) -> list[Permission]:
        model = self._db.get(RoleModel, role_id)
        return [p.to_entity() for p in (model.permissions if model else [])]

    def create(self, role: Role) -> Role:
        model = RoleModel(id=role.id, name=role.name, description=role.description, active=role.active)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update(self, role: Role) -> Role:
        model = self._db.get(RoleModel, role.id)
        if not model:
            return role
        model.name = role.name
        model.description = role.description
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def set_active(self, role_id: uuid.UUID, active: bool) -> Optional[Role]:
        model = self._db.get(RoleModel, role_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def replace_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> Optional[Role]:
        model = self._db.get(RoleModel, role_id)
        if not model:
            return None
        model.permissions = [p for p in (self._db.get(PermissionModel, pid) for pid in permission_ids) if p]
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def count_active_users_with_role(self, role_id: uuid.UUID) -> int:
        return self._db.query(UserModel).filter(UserModel.role_id == role_id, UserModel.active == True).count()

    def count_roles_with_permission(self, permission_id: uuid.UUID) -> int:
        return (
            self._db.query(role_permissions_table)
            .filter(role_permissions_table.c.permission_id == permission_id)
            .count()
        )


class PermissionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Permission]:
        models = self._db.query(PermissionModel).order_by(PermissionModel.module, PermissionModel.action).all()
        return [m.to_entity() for m in models]

    def get_by_id(self, permission_id: uuid.UUID) -> Optional[Permission]:
        model = self._db.get(PermissionModel, permission_id)
        return model.to_entity() if model else None

    def get_by_module_action(self, module: str, action: str) -> Optional[Permission]:
        model = self._db.query(PermissionModel).filter(
            PermissionModel.module == module, PermissionModel.action == action,
        ).first()
        return model.to_entity() if model else None

    def create(self, permission: Permission) -> Permission:
        model = PermissionModel(
            id=permission.id, module=permission.module, action=permission.action,
            description=permission.description,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def delete(self, permission_id: uuid.UUID) -> bool:
        model = self._db.get(PermissionModel, permission_id)
        if not model:
            return False
        self._db.delete(model)
        self._db.commit()
        return True
