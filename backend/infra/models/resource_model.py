import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Table, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.resource import Resource, Skill

resource_skills_table = Table(
    "resource_skills",
    Base.metadata,
    Column("resource_id", UUID(as_uuid=True), ForeignKey("resources.id"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
    Column("assigned_at", TIMESTAMP(timezone=True), server_default=text("now()")),
)


class SkillModel(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    code = Column(Text, nullable=False, unique=True)
    label = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> Skill:
        return Skill(id=self.id, code=self.code, label=self.label, active=self.active, created_at=self.created_at)


class ResourceModel(Base):
    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, unique=True)
    full_name = Column(Text, nullable=False)
    email = Column(Text, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    skills = relationship("SkillModel", secondary=resource_skills_table, lazy="joined")

    def to_entity(self) -> Resource:
        return Resource(
            id=self.id,
            user_id=self.user_id,
            full_name=self.full_name,
            email=self.email,
            active=self.active,
            notes=self.notes,
            skills=[s.to_entity() for s in (self.skills or [])],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
