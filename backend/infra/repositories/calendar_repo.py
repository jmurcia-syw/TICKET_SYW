from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend.infra.models.calendar_model import (
    HolidayModel, WorkScheduleModel, AbsenceRequestModel, AbsenceRequestAttachmentModel,
)
from backend.infra.models.resource_model import ResourceModel
from backend.domain.entities.calendar import (
    Holiday, WorkScheduleSlot, AbsenceRequest, AbsenceRequestAttachment,
)


class HolidayRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_country(self, country: str, active: bool | None = True) -> list[Holiday]:
        q = self._db.query(HolidayModel).filter(HolidayModel.country == country)
        if active is not None:
            q = q.filter(HolidayModel.active == active)
        return [m.to_entity() for m in q.order_by(HolidayModel.holiday_date).all()]

    def list_by_countries(self, countries: list[str], active: bool | None = True) -> list[Holiday]:
        if not countries:
            return []
        q = self._db.query(HolidayModel).filter(HolidayModel.country.in_(countries))
        if active is not None:
            q = q.filter(HolidayModel.active == active)
        return [m.to_entity() for m in q.order_by(HolidayModel.holiday_date).all()]

    def get_by_id(self, holiday_id: uuid.UUID) -> Optional[Holiday]:
        model = self._db.get(HolidayModel, holiday_id)
        return model.to_entity() if model else None

    def create(self, holiday: Holiday) -> Holiday:
        model = HolidayModel(id=holiday.id, country=holiday.country,
                             holiday_date=holiday.holiday_date, name=holiday.name)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def exists(self, country: str, holiday_date: date, name: str) -> bool:
        return (
            self._db.query(HolidayModel.id)
            .filter(HolidayModel.country == country, HolidayModel.holiday_date == holiday_date,
                    HolidayModel.name == name)
            .first()
            is not None
        )

    def set_active(self, holiday_id: uuid.UUID, active: bool) -> Optional[Holiday]:
        model = self._db.get(HolidayModel, holiday_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()


class WorkScheduleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_resource(self, resource_id: uuid.UUID) -> list[WorkScheduleSlot]:
        models = (
            self._db.query(WorkScheduleModel)
            .filter(WorkScheduleModel.resource_id == resource_id)
            .order_by(WorkScheduleModel.weekday)
            .all()
        )
        return [m.to_entity() for m in models]

    def replace_for_resource(self, resource_id: uuid.UUID, slots: list[WorkScheduleSlot]) -> list[WorkScheduleSlot]:
        """Reemplaza por completo las franjas del recurso (FR-006, `PUT` idempotente)."""
        self._db.query(WorkScheduleModel).filter(WorkScheduleModel.resource_id == resource_id).delete()
        models = [
            WorkScheduleModel(id=s.id, resource_id=resource_id, weekday=s.weekday,
                              start_time=s.start_time, end_time=s.end_time)
            for s in slots
        ]
        self._db.add_all(models)
        self._db.commit()
        return self.list_by_resource(resource_id)


class AbsenceRequestRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, request_id: uuid.UUID) -> Optional[AbsenceRequest]:
        model = self._db.get(AbsenceRequestModel, request_id)
        return model.to_entity() if model else None

    def create(self, request: AbsenceRequest) -> AbsenceRequest:
        model = AbsenceRequestModel.from_entity(request)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def list_by_resource(self, resource_id: uuid.UUID) -> list[AbsenceRequest]:
        models = (
            self._db.query(AbsenceRequestModel)
            .filter(AbsenceRequestModel.resource_id == resource_id)
            .order_by(AbsenceRequestModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def list_by_manager(self, manager_resource_id: uuid.UUID) -> list[AbsenceRequest]:
        """Solicitudes de los subordinados directos de `manager_resource_id` (FR-010a)."""
        models = (
            self._db.query(AbsenceRequestModel)
            .join(ResourceModel, ResourceModel.id == AbsenceRequestModel.resource_id)
            .filter(ResourceModel.manager_id == manager_resource_id)
            .order_by(AbsenceRequestModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def list_all(self) -> list[AbsenceRequest]:
        models = self._db.query(AbsenceRequestModel).order_by(AbsenceRequestModel.created_at.desc()).all()
        return [m.to_entity() for m in models]

    def list_overlapping(self, resource_id: uuid.UUID, start_date: date, end_date: date,
                         exclude_id: uuid.UUID | None = None) -> list[AbsenceRequest]:
        """Solicitudes propias vigentes (`pending`/`approved` en cualquiera de los dos lados)
        que se solapan con el rango dado (FR-009)."""
        q = (
            self._db.query(AbsenceRequestModel)
            .filter(
                AbsenceRequestModel.resource_id == resource_id,
                AbsenceRequestModel.start_date <= end_date,
                AbsenceRequestModel.end_date >= start_date,
                AbsenceRequestModel.manager_status != "rejected",
                AbsenceRequestModel.hr_status != "rejected",
            )
        )
        if exclude_id:
            q = q.filter(AbsenceRequestModel.id != exclude_id)
        return [m.to_entity() for m in q.all()]

    def get_active_absence(self, resource_id: uuid.UUID, on_date: date) -> Optional[AbsenceRequest]:
        """Solicitud con `overall_status=approved` (ambos lados `approved`) vigente en `on_date`
        (FR-013). Usada por `availability_service` vía la ruta de disponibilidad."""
        model = (
            self._db.query(AbsenceRequestModel)
            .filter(
                AbsenceRequestModel.resource_id == resource_id,
                AbsenceRequestModel.manager_status == "approved",
                AbsenceRequestModel.hr_status == "approved",
                AbsenceRequestModel.start_date <= on_date,
                AbsenceRequestModel.end_date >= on_date,
            )
            .first()
        )
        return model.to_entity() if model else None

    def update_decision(self, request_id: uuid.UUID, *, manager_status: str | None = None,
                        manager_decided_by: uuid.UUID | None = None,
                        hr_status: str | None = None,
                        hr_decided_by: uuid.UUID | None = None) -> Optional[AbsenceRequest]:
        model = self._db.get(AbsenceRequestModel, request_id)
        if not model:
            return None
        now = datetime.utcnow()
        if manager_status is not None:
            model.manager_status = manager_status
            model.manager_decided_by = manager_decided_by
            model.manager_decided_at = now
        if hr_status is not None:
            model.hr_status = hr_status
            model.hr_decided_by = hr_decided_by
            model.hr_decided_at = now
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    # ── Adjuntos (FR-008a) ──────────────────────────────────────────────────

    def list_attachments(self, absence_request_id: uuid.UUID) -> list[AbsenceRequestAttachment]:
        models = (
            self._db.query(AbsenceRequestAttachmentModel)
            .filter(AbsenceRequestAttachmentModel.absence_request_id == absence_request_id)
            .order_by(AbsenceRequestAttachmentModel.created_at)
            .all()
        )
        return [m.to_entity() for m in models]

    def add_attachment(self, attachment: AbsenceRequestAttachment) -> AbsenceRequestAttachment:
        model = AbsenceRequestAttachmentModel.from_entity(attachment)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def get_attachment(self, absence_request_id: uuid.UUID, attachment_id: uuid.UUID) -> Optional[AbsenceRequestAttachment]:
        model = self._db.get(AbsenceRequestAttachmentModel, attachment_id)
        if not model or model.absence_request_id != absence_request_id:
            return None
        return model.to_entity()

    def delete_attachment(self, absence_request_id: uuid.UUID, attachment_id: uuid.UUID) -> bool:
        model = self._db.get(AbsenceRequestAttachmentModel, attachment_id)
        if not model or model.absence_request_id != absence_request_id:
            return False
        self._db.delete(model)
        self._db.commit()
        return True
