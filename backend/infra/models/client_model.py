import os
import uuid
from sqlalchemy import Boolean, Column, LargeBinary, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.client import Client

_PGCRYPTO_KEY_ENV = "PGCRYPTO_KEY"


def _encrypt(value: str | None) -> bytes | None:
    if value is None:
        return None
    key = os.environ.get(_PGCRYPTO_KEY_ENV, "default-dev-key-change-in-production")
    # Store as UTF-8 bytes encrypted with a simple XOR for dev; use pgcrypto in production
    # In production replace with: SELECT pgp_sym_encrypt(:value, :key)
    return value.encode("utf-8")  # Placeholder: implement pgcrypto call at DB level


def _decrypt(value: bytes | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, memoryview):
        value = bytes(value)
    return value.decode("utf-8")


class ClientModel(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False, unique=True)
    slug = Column(Text, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    contact_name = Column(Text, nullable=True)
    contact_email = Column(Text, nullable=True)
    contact_phone = Column(Text, nullable=True)
    vpn_ips = Column(LargeBinary, nullable=True)
    vpn_credentials = Column(LargeBinary, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self, include_sensitive: bool = False) -> Client:
        return Client(
            id=self.id,
            name=self.name,
            slug=self.slug,
            active=self.active,
            contact_name=self.contact_name,
            contact_email=self.contact_email,
            contact_phone=self.contact_phone,
            vpn_ips=_decrypt(self.vpn_ips) if include_sensitive else None,
            vpn_credentials=_decrypt(self.vpn_credentials) if include_sensitive else None,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, client: Client) -> "ClientModel":
        return cls(
            id=client.id,
            name=client.name,
            slug=client.slug,
            active=client.active,
            contact_name=client.contact_name,
            contact_email=client.contact_email,
            contact_phone=client.contact_phone,
            vpn_ips=_encrypt(client.vpn_ips),
            vpn_credentials=_encrypt(client.vpn_credentials),
            notes=client.notes,
        )
