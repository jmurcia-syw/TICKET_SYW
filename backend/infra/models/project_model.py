import uuid
from sqlalchemy import Boolean, Column, Date, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.project import Project


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    start_date = Column(Date, nullable=False)
    end_date_estimated = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self) -> Project:
        return Project(
            id=self.id,
            client_id=self.client_id,
            name=self.name,
            description=self.description,
            active=self.active,
            start_date=self.start_date,
            end_date_estimated=self.end_date_estimated,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, project: Project) -> "ProjectModel":
        return cls(
            id=project.id,
            client_id=project.client_id,
            name=project.name,
            description=project.description,
            active=project.active,
            start_date=project.start_date,
            end_date_estimated=project.end_date_estimated,
        )
