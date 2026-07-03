from dataclasses import dataclass, field
from datetime import datetime
import uuid

EVENT_TYPES = (
    "assigned", "user_replied", "resolution_rejected", "closed", "close_eligible",
)


@dataclass
class Notification:
    id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    ticket_id: uuid.UUID
    message: str
    read: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, user_id: uuid.UUID, event_type: str, ticket_id: uuid.UUID,
               message: str) -> "Notification":
        return cls(id=uuid.uuid4(), user_id=user_id, event_type=event_type,
                   ticket_id=ticket_id, message=message)
