from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend.infra.models.calendar_model import (
    HolidayModel, HolidaySyncStatusModel, WorkScheduleModel, AbsenceRequestModel,
    AbsenceRequestAttachmentModel, WorkHourTemplateModel, WorkHourTemplateSlotModel,
)
from backend.infra.models.resource_model import ResourceModel
from backend.domain.entities.calendar import (
    Holiday, WorkScheduleSlot, AbsenceRequest, AbsenceRequestAttachment,
    WorkHourTemplate, WorkHourTemplateSlot,
)


class HolidayRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_country(self, country: str, active: bool | None = True,
                        category: str | None = None) -> list[Holiday]:
        q = self._db.query(HolidayModel).filter(HolidayModel.country == country)
        if active is not None:
            q = q.filter(HolidayModel.active == active)
        if category is not None:
            q = q.filter(HolidayModel.category == category)
        return [m.to_entity() for m in q.order_by(HolidayModel.holiday_date).all()]

    def list_by_countries(self, countries: list[str], active: bool | None = True,
                          category: str | None = None) -> list[Holiday]:
        if not countries:
            return []
        q = self._db.query(HolidayModel).filter(HolidayModel.country.in_(countries))
        if active is not None:
            q = q.filter(HolidayModel.active == active)
        if category is not None:
            q = q.filter(HolidayModel.category == category)
        return [m.to_entity() for m in q.order_by(HolidayModel.holiday_date).all()]

    def get_by_id(self, holiday_id: uuid.UUID) -> Optional[Holiday]:
        model = self._db.get(HolidayModel, holiday_id)
        return model.to_entity() if model else None

    def create(self, holiday: Holiday) -> Holiday:
        """Creación manual (vía Maestros) — siempre queda con `source='manual'` (FR-009/FR-010),
        sin importar lo que traiga la entidad."""
        model = HolidayModel(id=holiday.id, country=holiday.country,
                             holiday_date=holiday.holiday_date, name=holiday.name,
                             category=holiday.category, source="manual")
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

    def has_manual_holiday_on_date(self, country: str, holiday_date: date) -> bool:
        """Usado por la sincronización (research.md Decisión 6): si ya existe un festivo
        editado/creado a mano en esa fecha (cualquier nombre), no se inserta el de la API para
        evitar un duplicado nombre-distinto del mismo feriado."""
        return (
            self._db.query(HolidayModel.id)
            .filter(HolidayModel.country == country, HolidayModel.holiday_date == holiday_date,
                    HolidayModel.source == "manual")
            .first()
            is not None
        )

    def upsert_api_holiday(self, country: str, holiday_date: date, name: str,
                           category: str = "oficial") -> bool:
        """Inserta un festivo sincronizado desde la API si no colisiona con un festivo manual
        existente en la misma fecha, ni con una fila ya sincronizada antes (idempotente).
        Devuelve `True` si insertó una fila nueva."""
        if self.has_manual_holiday_on_date(country, holiday_date):
            return False
        if self.exists(country, holiday_date, name):
            return False
        model = HolidayModel(id=uuid.uuid4(), country=country, holiday_date=holiday_date,
                             name=name, category=category, source="api")
        self._db.add(model)
        self._db.commit()
        return True

    def set_active(self, holiday_id: uuid.UUID, active: bool) -> Optional[Holiday]:
        model = self._db.get(HolidayModel, holiday_id)
        if not model:
            return None
        model.active = active
        model.source = "manual"
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update(self, holiday_id: uuid.UUID, *, name: str | None = None,
              holiday_date: date | None = None, category: str | None = None) -> Optional[Holiday]:
        """Edición manual (FR-009): fuerza `source='manual'` sin importar el valor previo, para
        que la sincronización automática nunca vuelva a sobrescribir esta fila."""
        model = self._db.get(HolidayModel, holiday_id)
        if not model:
            return None
        if name is not None:
            model.name = name
        if holiday_date is not None:
            model.holiday_date = holiday_date
        if category is not None:
            model.category = category
        model.source = "manual"
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()


class HolidaySyncStatusRepository:
    """Estado operativo de sincronización de festivos por país/año (spec 021, sin RLS)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, country: str, year: int) -> Optional[HolidaySyncStatusModel]:
        return (
            self._db.query(HolidaySyncStatusModel)
            .filter(HolidaySyncStatusModel.country == country, HolidaySyncStatusModel.year == year)
            .first()
        )

    def record_attempt(self, country: str, year: int, success: bool,
                       error_message: str | None = None) -> None:
        existing = self.get(country, year)
        if existing:
            existing.success = success
            existing.error_message = error_message
            existing.last_synced_at = datetime.utcnow()
        else:
            self._db.add(HolidaySyncStatusModel(
                id=uuid.uuid4(), country=country, year=year, success=success,
                error_message=error_message,
            ))
        self._db.commit()


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

    def list_approved_between(self, resource_id: uuid.UUID, start_date: date,
                              end_date: date) -> list[AbsenceRequest]:
        """Solicitudes con ambos lados `approved` que se solapan con `[start_date, end_date]`
        (spec 022, research.md Decisión 11) — usado por `compute_available_seconds` para sumar
        disponibilidad a lo largo de un rango multi-día (`sla_last_resume_at` -> `now`).
        `get_active_absence` es de un solo día; `list_overlapping` incluye `pending`; ninguno de
        los dos alcanza para este cálculo."""
        models = (
            self._db.query(AbsenceRequestModel)
            .filter(
                AbsenceRequestModel.resource_id == resource_id,
                AbsenceRequestModel.manager_status == "approved",
                AbsenceRequestModel.hr_status == "approved",
                AbsenceRequestModel.start_date <= end_date,
                AbsenceRequestModel.end_date >= start_date,
            )
            .all()
        )
        return [m.to_entity() for m in models]

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


class WorkHourTemplateRepository:
    """Franja Horaria global por país (spec 022, FR-001/FR-002) — Capa 2. La persistencia vive
    aquí, no en `work_hour_template_service.py` (Capa 1, solo validación — research.md
    Decisión 12)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_country(self, country: str, active: bool | None = None) -> list[WorkHourTemplate]:
        q = self._db.query(WorkHourTemplateModel).filter(WorkHourTemplateModel.country == country)
        if active is not None:
            q = q.filter(WorkHourTemplateModel.active == active)
        return [m.to_entity() for m in q.order_by(WorkHourTemplateModel.name).all()]

    def get_by_id(self, template_id: uuid.UUID) -> Optional[WorkHourTemplate]:
        model = self._db.get(WorkHourTemplateModel, template_id)
        return model.to_entity() if model else None

    def create(self, template: WorkHourTemplate, slots: list[WorkHourTemplateSlot]) -> WorkHourTemplate:
        model = WorkHourTemplateModel(id=template.id, country=template.country, name=template.name,
                                      timezone=template.timezone, active=template.active)
        self._db.add(model)
        self._db.flush()
        self._db.add_all([
            WorkHourTemplateSlotModel(id=s.id, template_id=model.id, weekday=s.weekday,
                                      start_time=s.start_time, end_time=s.end_time)
            for s in slots
        ])
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update(self, template_id: uuid.UUID, *, name: str | None = None,
              timezone: str | None = None, active: bool | None = None) -> Optional[WorkHourTemplate]:
        model = self._db.get(WorkHourTemplateModel, template_id)
        if not model:
            return None
        if name is not None:
            model.name = name
        if timezone is not None:
            model.timezone = timezone
        if active is not None:
            model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def list_slots(self, template_id: uuid.UUID) -> list[WorkHourTemplateSlot]:
        models = (
            self._db.query(WorkHourTemplateSlotModel)
            .filter(WorkHourTemplateSlotModel.template_id == template_id)
            .order_by(WorkHourTemplateSlotModel.weekday)
            .all()
        )
        return [m.to_entity() for m in models]

    def replace_slots(self, template_id: uuid.UUID,
                      slots: list[WorkHourTemplateSlot]) -> list[WorkHourTemplateSlot]:
        self._db.query(WorkHourTemplateSlotModel).filter(
            WorkHourTemplateSlotModel.template_id == template_id).delete()
        models = [
            WorkHourTemplateSlotModel(id=s.id, template_id=template_id, weekday=s.weekday,
                                      start_time=s.start_time, end_time=s.end_time)
            for s in slots
        ]
        self._db.add_all(models)
        self._db.commit()
        return self.list_slots(template_id)


def resolve_effective_schedule_slots(db: Session, resource) -> list[WorkScheduleSlot]:
    """Resuelve el horario efectivo de `resource` según su `schedule_mode` (spec 022, FR-004):
    `personalizado` -> sus propias filas de `work_schedules`; `heredado` -> los slots de su
    `WorkHourTemplate` (convertidos al shape de `WorkScheduleSlot` para reusar
    `availability_service._within_schedule` sin cambios), o lista vacía si aún no tiene
    plantilla asignada (cae al default hardcodeado L-V 08:00-17:00, comportamiento ya
    existente). Único punto de resolución reusado por US1 (endpoint de disponibilidad ya
    existente), US2 (motor de SLA dinámico) y el endpoint de carga de trabajo."""
    if resource.schedule_mode == "personalizado" or not resource.work_hour_template_id:
        return WorkScheduleRepository(db).list_by_resource(resource.id)
    template_slots = WorkHourTemplateRepository(db).list_slots(resource.work_hour_template_id)
    return [
        WorkScheduleSlot(id=s.id, resource_id=resource.id, weekday=s.weekday,
                        start_time=s.start_time, end_time=s.end_time)
        for s in template_slots
    ]
