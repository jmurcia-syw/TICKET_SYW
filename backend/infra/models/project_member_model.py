import uuid
from sqlalchemy import Column, ForeignKey, Table, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.project_member import ProjectMember, ProjectTeam

project_team_members_table = Table(
    "project_team_members",
    Base.metadata,
    Column("team_id", UUID(as_uuid=True),
           ForeignKey("project_teams.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", UUID(as_uuid=True),
           ForeignKey("project_members.id", ondelete="CASCADE"), primary_key=True),
)


class ProjectMemberModel(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> ProjectMember:
        return ProjectMember(id=self.id, project_id=self.project_id,
                             user_id=self.user_id, assigned_at=self.assigned_at)


class ProjectTeamModel(Base):
    __tablename__ = "project_teams"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_teams_project_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> ProjectTeam:
        return ProjectTeam(id=self.id, project_id=self.project_id,
                           name=self.name, created_at=self.created_at)
