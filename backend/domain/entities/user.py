from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class Role(str, Enum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    QM = "qm"
    RESOLVER = "resolver"


@dataclass
class User:
    id: uuid.UUID
    email: str
    role: Role
    active: bool = True
    google_sub: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def has_role(self, *roles: Role) -> bool:
        return self.role in roles

    def can_access_sensitive_data(self) -> bool:
        return self.role in (Role.ADMIN, Role.COORDINATOR)
