from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import re


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")


@dataclass
class Client:
    id: uuid.UUID
    name: str
    slug: str
    active: bool = True
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    vpn_ips: Optional[str] = None
    vpn_credentials: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, name: str, **kwargs) -> "Client":
        return cls(id=uuid.uuid4(), name=name, slug=_slugify(name), **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
