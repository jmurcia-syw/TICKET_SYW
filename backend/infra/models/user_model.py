from sqlalchemy import Boolean, CheckConstraint, Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.user import User, Role
import uuid


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    email = Column(Text, nullable=False, unique=True)
    role = Column(Text, nullable=False, default="resolver")
    active = Column(Boolean, nullable=False, default=True)
    google_sub = Column(Text, nullable=True, unique=True)
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('admin','coordinator','qm','resolver')", name="ck_users_role"),
        CheckConstraint("email LIKE '%@sywork.net'", name="ck_users_email_domain"),
    )

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            role=Role(self.role),
            active=self.active,
            google_sub=self.google_sub,
            last_login_at=self.last_login_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role.value,
            active=user.active,
            google_sub=user.google_sub,
            last_login_at=user.last_login_at,
        )
