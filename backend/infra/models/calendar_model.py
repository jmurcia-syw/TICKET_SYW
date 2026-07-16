import uuid
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, SmallInteger, Text, Time, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.calendar import (
    Holiday, WorkScheduleSlot, AbsenceRequest, AbsenceRequestAttachment,
)


class HolidayModel(Base):
    __tablename__ = "holidays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    country = Column(Text, nullable=False)
    holiday_date = Column(Date, nullable=False)
    name = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> Holiday:
        return Holiday(id=self.id, country=self.country, holiday_date=self.holiday_date,
                       name=self.name, active=self.active, created_at=self.created_at)


class WorkScheduleModel(Base):
    __tablename__ = "work_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    weekday = Column(SmallInteger, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> WorkScheduleSlot:
        return WorkScheduleSlot(id=self.id, resource_id=self.resource_id, weekday=self.weekday,
                                start_time=self.start_time, end_time=self.end_time,
                                created_at=self.created_at)


class AbsenceRequestModel(Base):
    __tablename__ = "absence_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=False)
    absence_type_id = Column(UUID(as_uuid=True), ForeignKey("catalog_absence_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    manager_status = Column(Text, nullable=False, default="pending")
    manager_decided_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    manager_decided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    hr_status = Column(Text, nullable=False, default="pending")
    hr_decided_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    hr_decided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self) -> AbsenceRequest:
        return AbsenceRequest(
            id=self.id, resource_id=self.resource_id, absence_type_id=self.absence_type_id,
            start_date=self.start_date, end_date=self.end_date,
            manager_status=self.manager_status, manager_decided_by=self.manager_decided_by,
            manager_decided_at=self.manager_decided_at,
            hr_status=self.hr_status, hr_decided_by=self.hr_decided_by,
            hr_decided_at=self.hr_decided_at, notes=self.notes,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, request: AbsenceRequest) -> "AbsenceRequestModel":
        return cls(
            id=request.id, resource_id=request.resource_id, absence_type_id=request.absence_type_id,
            start_date=request.start_date, end_date=request.end_date,
            manager_status=request.manager_status, notes=request.notes,
        )


class AbsenceRequestAttachmentModel(Base):
    __tablename__ = "absence_request_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    absence_request_id = Column(UUID(as_uuid=True), ForeignKey("absence_requests.id", ondelete="CASCADE"), nullable=False)
    filename = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> AbsenceRequestAttachment:
        return AbsenceRequestAttachment(
            id=self.id, absence_request_id=self.absence_request_id, filename=self.filename,
            content_type=self.content_type, size_bytes=self.size_bytes,
            storage_path=self.storage_path, created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, attachment: AbsenceRequestAttachment) -> "AbsenceRequestAttachmentModel":
        return cls(
            id=attachment.id, absence_request_id=attachment.absence_request_id,
            filename=attachment.filename, content_type=attachment.content_type,
            size_bytes=attachment.size_bytes, storage_path=attachment.storage_path,
        )
