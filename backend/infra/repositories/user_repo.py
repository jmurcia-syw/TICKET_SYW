from typing import Optional
from sqlalchemy.orm import Session
from backend.infra.models.user_model import UserModel
from backend.domain.entities.user import User, Role
import uuid


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        return model.to_entity() if model else None

    def get_by_email(self, email: str) -> Optional[User]:
        model = self._db.query(UserModel).filter(UserModel.email == email).first()
        return model.to_entity() if model else None

    def get_by_google_sub(self, google_sub: str) -> Optional[User]:
        model = self._db.query(UserModel).filter(UserModel.google_sub == google_sub).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, role: Optional[str] = None, active: Optional[bool] = None) -> tuple[list[User], int]:
        q = self._db.query(UserModel)
        if role:
            q = q.filter(UserModel.role == role)
        if active is not None:
            q = q.filter(UserModel.active == active)
        total = q.count()
        models = q.offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, user: User) -> User:
        model = UserModel.from_entity(user)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update_role(self, user_id: uuid.UUID, role: Role) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        if not model:
            return None
        model.role = role.value
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def set_active(self, user_id: uuid.UUID, active: bool) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update_last_login(self, user_id: uuid.UUID) -> None:
        from sqlalchemy.sql import func
        self._db.query(UserModel).filter(UserModel.id == user_id).update({"last_login_at": func.now()})
        self._db.commit()

    def count_active_admins(self) -> int:
        return self._db.query(UserModel).filter(UserModel.role == "admin", UserModel.active == True).count()
