from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class TaskList:
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    position: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
