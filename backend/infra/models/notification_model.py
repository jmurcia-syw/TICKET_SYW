import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.notification import Notification


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(Text, nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> Notification:
        return Notification(
            id=self.id, user_id=self.user_id, event_type=self.event_type,
            ticket_id=self.ticket_id, message=self.message, read=self.read,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, n: Notification) -> "NotificationModel":
        return cls(id=n.id, user_id=n.user_id, event_type=n.event_type,
                   ticket_id=n.ticket_id, message=n.message, read=n.read)
