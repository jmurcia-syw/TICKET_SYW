from typing import Optional
from sqlalchemy.orm import Session
from backend.infra.models.client_model import ClientModel
from backend.domain.entities.client import Client
import uuid


class ClientRepository:
    def __init__(self, db: Session, include_sensitive: bool = False) -> None:
        self._db = db
        self._include_sensitive = include_sensitive

    def get_by_id(self, client_id: uuid.UUID, include_sensitive: bool | None = None) -> Optional[Client]:
        model = self._db.get(ClientModel, client_id)
        if not model:
            return None
        sensitive = include_sensitive if include_sensitive is not None else self._include_sensitive
        return model.to_entity(include_sensitive=sensitive)

    def get_by_name(self, name: str) -> Optional[Client]:
        model = self._db.query(ClientModel).filter(ClientModel.name == name).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, search: str | None = None, active: bool | None = None) -> tuple[list[Client], int]:
        q = self._db.query(ClientModel)
        if search:
            q = q.filter(ClientModel.name.ilike(f"%{search}%"))
        if active is not None:
            q = q.filter(ClientModel.active == active)
        total = q.count()
        models = q.order_by(ClientModel.name).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, client: Client) -> Client:
        model = ClientModel.from_entity(client)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity(include_sensitive=self._include_sensitive)

    def update(self, client: Client) -> Client:
        model = self._db.get(ClientModel, client.id)
        if not model:
            return client
        for field in ("name", "slug", "active", "contact_name", "contact_email", "contact_phone", "notes"):
            setattr(model, field, getattr(client, field))
        if client.vpn_ips is not None:
            from backend.infra.models.client_model import _encrypt
            model.vpn_ips = _encrypt(client.vpn_ips)
        if client.vpn_credentials is not None:
            from backend.infra.models.client_model import _encrypt
            model.vpn_credentials = _encrypt(client.vpn_credentials)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity(include_sensitive=self._include_sensitive)

    def deactivate(self, client_id: uuid.UUID) -> Optional[Client]:
        model = self._db.get(ClientModel, client_id)
        if not model:
            return None
        model.active = False
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()
