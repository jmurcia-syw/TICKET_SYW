from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Role:
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, name: str, description: Optional[str] = None) -> "Role":
        return cls(id=uuid.uuid4(), name=name, description=description)


@dataclass
class Permission:
    id: uuid.UUID
    module: str
    action: str
    description: Optional[str] = None

    @classmethod
    def create(cls, module: str, action: str, description: Optional[str] = None) -> "Permission":
        return cls(id=uuid.uuid4(), module=module, action=action, description=description)
