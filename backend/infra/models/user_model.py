from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.user import User
import uuid


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    email = Column(Text, nullable=False, unique=True)
    username = Column(Text, nullable=False, unique=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    password_hash = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    google_sub = Column(Text, nullable=True, unique=True)
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    role = relationship("RoleModel", lazy="joined")

    __table_args__ = (
        CheckConstraint("email LIKE '%@sywork.net'", name="ck_users_email_domain"),
    )

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            username=self.username,
            role=self.role.to_entity(),
            active=self.active,
            google_sub=self.google_sub,
            password_hash=self.password_hash,
            last_login_at=self.last_login_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            role_id=user.role.id,
            password_hash=user.password_hash,
            active=user.active,
            google_sub=user.google_sub,
        )
