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
class ClientSystem:
    """Sistema de software que posee el cliente (FR-029, SDD V3)."""
    id: uuid.UUID
    client_id: uuid.UUID
    system_type: str
    brand: str
    version: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, client_id: uuid.UUID, system_type: str, brand: str, **kwargs) -> "ClientSystem":
        return cls(id=uuid.uuid4(), client_id=client_id, system_type=system_type, brand=brand, **kwargs)


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
    annual_billing_usd: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, name: str, **kwargs) -> "Client":
        return cls(id=uuid.uuid4(), name=name, slug=_slugify(name), **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
