import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from backend.infra.models import Base
from backend.domain.entities.sla_rule import SlaRule


class SlaRuleModel(Base):
    __tablename__ = "sla_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    priority = Column(Text, nullable=False)
    contact_minutes = Column(Integer, nullable=False)
    execution_minutes = Column(Integer, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self) -> SlaRule:
        return SlaRule(
            id=self.id, project_id=self.project_id, priority=self.priority,
            contact_minutes=self.contact_minutes, execution_minutes=self.execution_minutes,
            active=self.active, created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, rule: SlaRule) -> "SlaRuleModel":
        return cls(
            id=rule.id, project_id=rule.project_id, priority=rule.priority,
            contact_minutes=rule.contact_minutes, execution_minutes=rule.execution_minutes,
            active=rule.active,
        )
