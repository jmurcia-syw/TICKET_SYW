import uuid
from sqlalchemy import Column, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.client_contact import ClientContact


class ClientContactModel(Base):
    __tablename__ = "client_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> ClientContact:
        return ClientContact(
            id=self.id, user_id=self.user_id, client_id=self.client_id, created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, contact: ClientContact) -> "ClientContactModel":
        return cls(id=contact.id, user_id=contact.user_id, client_id=contact.client_id)
