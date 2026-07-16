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
    """Día festivo de un país (FR-003)."""
    id: uuid.UUID
    country: str
    holiday_date: date
    name: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, country: str, holiday_date: date, name: str) -> "Holiday":
        return cls(id=uuid.uuid4(), country=country, holiday_date=holiday_date, name=name)


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
    FR-012a). `overall_status` se deriva en `absence_service`, no se persiste."""
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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, resource_id: uuid.UUID, absence_type_id: uuid.UUID, start_date: date,
               end_date: date, notes: Optional[str] = None,
               manager_status: str = "pending") -> "AbsenceRequest":
        return cls(id=uuid.uuid4(), resource_id=resource_id, absence_type_id=absence_type_id,
                   start_date=start_date, end_date=end_date, notes=notes,
                   manager_status=manager_status)


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
class Availability:
    """Resultado del cálculo de disponibilidad de un recurso en un instante dado (FR-013 a
    FR-016). Value object — no se persiste."""
    available: bool
    reason: Optional[str] = None
    detail: Optional[str] = None
