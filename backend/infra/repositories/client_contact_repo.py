from typing import Optional
import uuid
from sqlalchemy.orm import Session
from backend.infra.models.client_contact_model import ClientContactModel
from backend.domain.entities.client_contact import ClientContact


class ClientContactRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[ClientContact]:
        model = self._db.query(ClientContactModel).filter(ClientContactModel.user_id == user_id).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20,
                       client_id: Optional[uuid.UUID] = None) -> tuple[list[ClientContact], int]:
        q = self._db.query(ClientContactModel)
        if client_id:
            q = q.filter(ClientContactModel.client_id == client_id)
        total = q.count()
        models = q.order_by(ClientContactModel.created_at).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, contact: ClientContact) -> ClientContact:
        model = ClientContactModel.from_entity(contact)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()
