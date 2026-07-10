from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.infra.models import Base
from backend.domain.entities.ticket_timer import TicketTimer


class TicketTimerModel(Base):
    __tablename__ = "ticket_timers"

    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True)
    status = Column(Text, nullable=False, server_default="inactive")
    accumulated_seconds = Column(Integer, nullable=False, server_default="0")
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self) -> TicketTimer:
        return TicketTimer(
            resource_id=self.resource_id,
            ticket_id=self.ticket_id,
            status=self.status,
            accumulated_seconds=self.accumulated_seconds,
            started_at=self.started_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, timer: TicketTimer) -> "TicketTimerModel":
        return cls(
            resource_id=timer.resource_id,
            ticket_id=timer.ticket_id,
            status=timer.status,
            accumulated_seconds=timer.accumulated_seconds,
            started_at=timer.started_at,
        )
