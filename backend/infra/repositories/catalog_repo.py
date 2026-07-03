from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend.infra.models.catalog_model import CATALOG_MODELS


class CatalogRepository:
    """Repositorio genérico para los 3 catálogos de tickets (tools/processes/resolution-types)."""

    def __init__(self, db: Session, catalog: str) -> None:
        if catalog not in CATALOG_MODELS:
            raise ValueError(f"Catálogo desconocido: {catalog}")
        self._db = db
        self._model = CATALOG_MODELS[catalog]

    def list_all(self, active: bool | None = True) -> list[dict]:
        q = self._db.query(self._model)
        if active is not None:
            q = q.filter(self._model.active == active)
        return [m.to_dict() for m in q.order_by(self._model.name).all()]

    def get_by_id(self, catalog_id: uuid.UUID) -> Optional[dict]:
        model = self._db.get(self._model, catalog_id)
        return model.to_dict() if model else None

    def get_by_name(self, name: str) -> Optional[dict]:
        model = self._db.query(self._model).filter(self._model.name == name).first()
        return model.to_dict() if model else None

    def create(self, name: str) -> dict:
        model = self._model(id=uuid.uuid4(), name=name)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_dict()

    def set_active(self, catalog_id: uuid.UUID, active: bool) -> Optional[dict]:
        model = self._db.get(self._model, catalog_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        return model.to_dict()
