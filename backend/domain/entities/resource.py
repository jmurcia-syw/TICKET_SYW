from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import uuid


SKILL_TYPES = ("funcional", "tecnico")


@dataclass
class Skill:
    id: uuid.UUID
    code: str
    label: str
    skill_type: str = "tecnico"
    tool_id: Optional[uuid.UUID] = None
    process_id: Optional[uuid.UUID] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, code: str, label: str, skill_type: str = "tecnico",
               tool_id: Optional[uuid.UUID] = None,
               process_id: Optional[uuid.UUID] = None) -> "Skill":
        return cls(id=uuid.uuid4(), code=code.upper(), label=label,
                   skill_type=skill_type, tool_id=tool_id, process_id=process_id)


@dataclass
class Resource:
    id: uuid.UUID
    full_name: str
    email: str
    active: bool = True
    user_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    skills: list[Skill] = field(default_factory=list)
    # Perfil extendido SDD V3 (FR-031) — todos opcionales
    identification: Optional[str] = None
    nationality: Optional[str] = None
    birth_date: Optional[date] = None
    marital_status: Optional[str] = None
    contract_type: Optional[str] = None
    calendar_country: Optional[str] = None
    education_level: Optional[str] = None
    specialty: Optional[str] = None
    seniority: Optional[str] = None
    certifications: Optional[str] = None
    team: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None
    # Huso horario del recurso (Fase 5, spec 020) — `calendar_country` ya define el país/festivos;
    # `timezone` es explícito porque un mismo país puede abarcar más de una zona horaria.
    timezone: Optional[str] = None
    # Franja Horaria global (spec 022, FR-003/FR-004): "heredado" resuelve el horario efectivo
    # desde `work_hour_template_id` en tiempo de lectura; "personalizado" usa las filas propias
    # de `work_schedules` (sin cambios de esquema en esa tabla).
    schedule_mode: str = "heredado"
    work_hour_template_id: Optional[uuid.UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, full_name: str, email: str, **kwargs) -> "Resource":
        return cls(id=uuid.uuid4(), full_name=full_name, email=email, **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
