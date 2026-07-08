from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ClientContact:
    id: uuid.UUID
    user_id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime = field(default_factory=datetime.utcnow)
