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
    # OBS-0026: tipos que no implican trabajo de resolución (ej. "No es incidente") pueden
    # cerrar el ticket sin tiempo registrado en work_sessions.
    allow_zero_time = Column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {**super().to_dict(), "allow_zero_time": self.allow_zero_time}


class RecordTypeCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_record_types"


class TeamCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_teams"


class AbsenceTypeCatalogModel(_CatalogMixin, Base):
    __tablename__ = "catalog_absence_types"


CATALOG_MODELS = {
    "tools": ToolCatalogModel,
    "processes": ProcessCatalogModel,
    "resolution-types": ResolutionTypeCatalogModel,
    "record-types": RecordTypeCatalogModel,
    "teams": TeamCatalogModel,
    "absence-types": AbsenceTypeCatalogModel,
}

# columna de tickets que referencia cada catálogo (para el bloqueo por uso). "teams" no aplica —
# el campo "Equipo" vive en `resources.team` (texto libre validado contra el catálogo, sin FK),
# no en tickets — se omite intencionalmente de este mapeo (OBS-0024).
CATALOG_TICKET_COLUMN = {
    "tools": "tool_id",
    "processes": "process_id",
    "resolution-types": "resolution_type_id",
    "record-types": "record_type_id",
}
