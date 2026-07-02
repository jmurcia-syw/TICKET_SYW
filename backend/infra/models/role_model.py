import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Table, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.role import Role, Permission

role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
)


class PermissionModel(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    module = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    def to_entity(self) -> Permission:
        return Permission(id=self.id, module=self.module, action=self.action, description=self.description)


class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    permissions = relationship("PermissionModel", secondary=role_permissions_table, lazy="joined")

    def to_entity(self) -> Role:
        return Role(
            id=self.id, name=self.name, description=self.description,
            active=self.active, created_at=self.created_at,
        )
