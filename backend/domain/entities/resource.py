from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import uuid


@dataclass
class Skill:
    id: uuid.UUID
    code: str
    label: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, code: str, label: str) -> "Skill":
        return cls(id=uuid.uuid4(), code=code.upper(), label=label)


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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, full_name: str, email: str, **kwargs) -> "Resource":
        return cls(id=uuid.uuid4(), full_name=full_name, email=email, **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
