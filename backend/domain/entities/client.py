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


ACCESS_TYPES = ("vpn", "system_url", "remote_desktop")
ACCESS_ENVIRONMENTS = ("dev", "test", "prod")


@dataclass
class ClientAccess:
    """Acceso/conexión de un cliente: VPN, URL de sistema por ambiente o escritorio remoto
    (spec 018 — reemplaza a los campos simples vpn_ips/vpn_credentials, UAT OBS-0001)."""
    id: uuid.UUID
    client_id: uuid.UUID
    access_type: str
    environment: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, client_id: uuid.UUID, access_type: str, **kwargs) -> "ClientAccess":
        return cls(id=uuid.uuid4(), client_id=client_id, access_type=access_type, **kwargs)


@dataclass
class ClientAccessAttachment:
    """Archivo adjunto a la sección de accesos y conexiones de un cliente (spec 018)."""
    id: uuid.UUID
    client_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)


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
    # Calendario del cliente (Fase 5, spec 020): huso horario y país de residencia, usados
    # para resaltar festivos en su calendario (FR-001/FR-004).
    timezone: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, name: str, **kwargs) -> "Client":
        return cls(id=uuid.uuid4(), name=name, slug=_slugify(name), **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
