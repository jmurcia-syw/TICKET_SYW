from typing import Optional
import uuid
from sqlalchemy.orm import Session
from backend.infra.models.client_contact_model import ClientContactModel
from backend.domain.entities.client_contact import ClientContact


class ClientContactRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, contact_id: uuid.UUID) -> Optional[ClientContact]:
        model = self._db.get(ClientContactModel, contact_id)
        return model.to_entity() if model else None

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[ClientContact]:
        model = self._db.query(ClientContactModel).filter(ClientContactModel.user_id == user_id).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20,
                       client_id: Optional[uuid.UUID] = None,
                       project_id: Optional[uuid.UUID] = None,
                       email: Optional[str] = None,
                       username: Optional[str] = None) -> tuple[list[ClientContact], int]:
        q = self._db.query(ClientContactModel)
        if client_id:
            q = q.filter(ClientContactModel.client_id == client_id)
        if project_id:
            # Spec 010 (US2): solo contactos vinculados al proyecto vía project_members
            from backend.infra.models.project_member_model import ProjectMemberModel
            q = q.join(ProjectMemberModel, ProjectMemberModel.user_id == ClientContactModel.user_id)
            q = q.filter(ProjectMemberModel.project_id == project_id)
        if email or username:
            # Spec 010 (ajuste post-implementación): filtros de listado por email/usuario
            from backend.infra.models.user_model import UserModel
            q = q.join(UserModel, UserModel.id == ClientContactModel.user_id)
            if email:
                q = q.filter(UserModel.email.ilike(f"%{email}%"))
            if username:
                q = q.filter(UserModel.username.ilike(f"%{username}%"))
        total = q.count()
        models = q.order_by(ClientContactModel.created_at).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, contact: ClientContact) -> ClientContact:
        model = ClientContactModel.from_entity(contact)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update_client_id(self, contact_id: uuid.UUID, client_id: uuid.UUID) -> None:
        model = self._db.get(ClientContactModel, contact_id)
        if not model:
            return
        model.client_id = client_id
        self._db.commit()
