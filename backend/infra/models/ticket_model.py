import uuid
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.ticket import Ticket


class TicketModel(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    ticket_number = Column(BigInteger, nullable=False, unique=True,
                           server_default=text("nextval('ticket_number_seq')"))
    record_type = Column(Text, nullable=False, default="ticket")
    ticket_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="nuevo")
    priority = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    escalation_level = Column(Text, nullable=False, default="n2")
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("catalog_tools.id"), nullable=True)
    process_id = Column(UUID(as_uuid=True), ForeignKey("catalog_processes.id"), nullable=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=True)
    estimated_resolution_minutes = Column(Integer, nullable=True)
    resolution_type_id = Column(UUID(as_uuid=True), ForeignKey("catalog_resolution_types.id"), nullable=True)
    related_ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolution_accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    closed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self) -> Ticket:
        return Ticket(
            id=self.id,
            ticket_number=self.ticket_number,
            record_type=self.record_type,
            ticket_type=self.ticket_type,
            title=self.title,
            description=self.description,
            status=self.status,
            priority=self.priority,
            severity=self.severity,
            escalation_level=self.escalation_level,
            client_id=self.client_id,
            project_id=self.project_id,
            tool_id=self.tool_id,
            process_id=self.process_id,
            assignee_id=self.assignee_id,
            estimated_resolution_minutes=self.estimated_resolution_minutes,
            resolution_type_id=self.resolution_type_id,
            related_ticket_id=self.related_ticket_id,
            created_by=self.created_by,
            resolved_at=self.resolved_at,
            resolution_accepted_at=self.resolution_accepted_at,
            closed_at=self.closed_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class StatusTransitionModel(Base):
    __tablename__ = "ticket_status_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    from_status = Column(Text, nullable=False)
    to_status = Column(Text, nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("ticket_comments.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class AssignmentModel(Base):
    __tablename__ = "ticket_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    assigner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=False)
    resulting_status = Column(Text, nullable=False)
    context = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
