from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from backend.domain.entities.role import Role


@dataclass
class User:
    id: uuid.UUID
    email: str
    username: str
    role: Role
    active: bool = True
    google_sub: Optional[str] = None
    password_hash: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    reset_token: Optional[str] = None
    reset_token_expires_at: Optional[datetime] = None

    def has_role(self, *role_names: str) -> bool:
        return self.role.name in role_names

    def can_access_sensitive_data(self) -> bool:
        return self.role.name in ("Admin", "Coordinador")
