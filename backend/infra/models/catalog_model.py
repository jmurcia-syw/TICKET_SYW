import uuid
from sqlalchemy import Boolean, Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base


class _CatalogMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_dict(self) -> dict:
        return {"id": str(self.id), "name": self.name, "active": self.active}


class ToolCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_tools"


class ProcessCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_processes"


class ResolutionTypeCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_resolution_types"


class RecordTypeCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_record_types"


CATALOG_MODELS = {
    "tools": ToolCatalogModel,
    "processes": ProcessCatalogModel,
    "resolution-types": ResolutionTypeCatalogModel,
    "record-types": RecordTypeCatalogModel,
}

# columna de tickets que referencia cada catálogo (para el bloqueo por uso)
CATALOG_TICKET_COLUMN = {
    "tools": "tool_id",
    "processes": "process_id",
    "resolution-types": "resolution_type_id",
    "record-types": "record_type_id",
}
