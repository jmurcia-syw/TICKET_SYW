from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Skill:
    id: uuid.UUID
    code: str
    label: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, code: str, label: str) -> "Skill":
        return cls(id=uuid.uuid4(), code=code.upper(), label=label)


@dataclass
class Resource:
    id: uuid.UUID
    full_name: str
    email: str
    active: bool = True
    user_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    skills: list[Skill] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, full_name: str, email: str, **kwargs) -> "Resource":
        return cls(id=uuid.uuid4(), full_name=full_name, email=email, **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
