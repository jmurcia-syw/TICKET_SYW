"""Entidades de dominio de Fase 5 (spec 020): festivos, horario laboral y ausencias.

Sin imports de Flask/SQLAlchemy (Principio I) — puro Python, dataclasses.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Optional
import uuid


ABSENCE_DECISION_STATUSES = ("pending", "approved", "rejected")


@dataclass
class Holiday:
    """Día festivo de un país (FR-003).

    `category` ("oficial" | "regional_religioso", spec 021 FR-005) distingue festivos de
    cumplimiento nacional de celebraciones locales/religiosas — solo "oficial" afecta el cálculo
    de disponibilidad (FR-007). `source` ("api" | "manual") marca si la fila vino de la
    sincronización automática o fue creada/editada a mano; una fila "manual" nunca es
    sobrescrita por la sincronización (FR-009).
    """
    id: uuid.UUID
    country: str
    holiday_date: date
    name: str
    active: bool = True
    category: str = "oficial"
    source: str = "manual"
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, country: str, holiday_date: date, name: str,
               category: str = "oficial", source: str = "manual") -> "Holiday":
        return cls(id=uuid.uuid4(), country=country, holiday_date=holiday_date, name=name,
                   category=category, source=source)


@dataclass
class WorkScheduleSlot:
    """Franja de horario laboral de un recurso para un día de la semana (FR-006).

    `weekday`: 0=lunes ... 6=domingo. Horas "naive", interpretadas en el `timezone` del propio
    recurso al evaluar disponibilidad.
    """
    id: uuid.UUID
    resource_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, resource_id: uuid.UUID, weekday: int, start_time: time, end_time: time) -> "WorkScheduleSlot":
        return cls(id=uuid.uuid4(), resource_id=resource_id, weekday=weekday,
                   start_time=start_time, end_time=end_time)


@dataclass
class AbsenceRequest:
    """Solicitud de ausencia (vacaciones, incapacidad médica, permiso personal, otro) con doble
    aprobación independiente: Jefe directo (`manager_status`) y RRHH (`hr_status`) (FR-008 a
    FR-012a). `overall_status` se deriva en `absence_service`, no se persiste.

    `start_time`/`end_time` (spec 022, FR-017): ambos `None` = ausencia de día completo
    (comportamiento original, sin cambios); ambos presentes = permiso parcial dentro de
    `start_date` (que debe igualar `end_date` en ese caso).
    """
    id: uuid.UUID
    resource_id: uuid.UUID
    absence_type_id: uuid.UUID
    start_date: date
    end_date: date
    manager_status: str = "pending"
    manager_decided_by: Optional[uuid.UUID] = None
    manager_decided_at: Optional[datetime] = None
    hr_status: str = "pending"
    hr_decided_by: Optional[uuid.UUID] = None
    hr_decided_at: Optional[datetime] = None
    notes: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, resource_id: uuid.UUID, absence_type_id: uuid.UUID, start_date: date,
               end_date: date, notes: Optional[str] = None,
               manager_status: str = "pending", start_time: Optional[time] = None,
               end_time: Optional[time] = None) -> "AbsenceRequest":
        return cls(id=uuid.uuid4(), resource_id=resource_id, absence_type_id=absence_type_id,
                   start_date=start_date, end_date=end_date, notes=notes,
                   manager_status=manager_status, start_time=start_time, end_time=end_time)


@dataclass
class AbsenceRequestAttachment:
    """Documento de soporte adjunto a una solicitud de ausencia (FR-008a)."""
    id: uuid.UUID
    absence_request_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkHourTemplate:
    """Franja Horaria global por país (spec 022, FR-001/FR-002): plantilla que un `Resource` con
    `schedule_mode == "heredado"` sigue automáticamente sin copiar filas (herencia por lectura)."""
    id: uuid.UUID
    country: str
    name: str
    timezone: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, country: str, name: str, timezone: str) -> "WorkHourTemplate":
        return cls(id=uuid.uuid4(), country=country, name=name, timezone=timezone)


@dataclass
class WorkHourTemplateSlot:
    """Franja semanal de una `WorkHourTemplate` (mismo shape que `WorkScheduleSlot`, FR-002)."""
    id: uuid.UUID
    template_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time

    @classmethod
    def create(cls, template_id: uuid.UUID, weekday: int, start_time: time, end_time: time) -> "WorkHourTemplateSlot":
        return cls(id=uuid.uuid4(), template_id=template_id, weekday=weekday,
                   start_time=start_time, end_time=end_time)


@dataclass
class Availability:
    """Resultado del cálculo de disponibilidad de un recurso en un instante dado (FR-013 a
    FR-016). Value object — no se persiste."""
    available: bool
    reason: Optional[str] = None
    detail: Optional[str] = None
