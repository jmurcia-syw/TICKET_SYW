import uuid
from sqlalchemy import Boolean, Column, Date, ForeignKey, LargeBinary, Table, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.resource import Resource, Skill
from backend.domain.entities.compensation import ResourceCompensation

resource_skills_table = Table(
    "resource_skills",
    Base.metadata,
    Column("resource_id", UUID(as_uuid=True), ForeignKey("resources.id"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
    Column("assigned_at", TIMESTAMP(timezone=True), server_default=text("now()")),
)


class SkillModel(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    code = Column(Text, nullable=False, unique=True)
    label = Column(Text, nullable=False)
    skill_type = Column(Text, nullable=False, default="tecnico")
    tool_id = Column(UUID(as_uuid=True), ForeignKey("catalog_tools.id"), nullable=True)
    process_id = Column(UUID(as_uuid=True), ForeignKey("catalog_processes.id"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> Skill:
        return Skill(id=self.id, code=self.code, label=self.label, skill_type=self.skill_type,
                     tool_id=self.tool_id, process_id=self.process_id,
                     active=self.active, created_at=self.created_at)


class ResourceModel(Base):
    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, unique=True)
    full_name = Column(Text, nullable=False)
    email = Column(Text, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    identification = Column(Text, nullable=True)
    nationality = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)
    marital_status = Column(Text, nullable=True)
    contract_type = Column(Text, nullable=True)
    calendar_country = Column(Text, nullable=True)
    education_level = Column(Text, nullable=True)
    specialty = Column(Text, nullable=True)
    seniority = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    team = Column(Text, nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    skills = relationship("SkillModel", secondary=resource_skills_table, lazy="joined")

    def to_entity(self) -> Resource:
        return Resource(
            id=self.id,
            user_id=self.user_id,
            full_name=self.full_name,
            email=self.email,
            active=self.active,
            notes=self.notes,
            identification=self.identification,
            nationality=self.nationality,
            birth_date=self.birth_date,
            marital_status=self.marital_status,
            contract_type=self.contract_type,
            calendar_country=self.calendar_country,
            education_level=self.education_level,
            specialty=self.specialty,
            seniority=self.seniority,
            certifications=self.certifications,
            team=self.team,
            manager_id=self.manager_id,
            skills=[s.to_entity() for s in (self.skills or [])],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


def _encrypt_amount(value: float | None) -> bytes | None:
    if value is None:
        return None
    # Placeholder dev: mismo patron que client_model; en produccion pgp_sym_encrypt
    return str(value).encode("utf-8")


def _decrypt_amount(value: bytes | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, memoryview):
        value = bytes(value)
    return float(value.decode("utf-8"))


class ResourceCompensationModel(Base):
    __tablename__ = "resource_compensation"

    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), primary_key=True)
    base_salary = Column(LargeBinary, nullable=True)
    total_salary = Column(LargeBinary, nullable=True)
    overhead = Column(LargeBinary, nullable=True)
    hourly_cost = Column(LargeBinary, nullable=True)
    currency = Column(Text, nullable=False, default="USD", server_default="USD")
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def to_entity(self) -> ResourceCompensation:
        return ResourceCompensation(
            resource_id=self.resource_id,
            base_salary=_decrypt_amount(self.base_salary),
            total_salary=_decrypt_amount(self.total_salary),
            overhead=_decrypt_amount(self.overhead),
            hourly_cost=_decrypt_amount(self.hourly_cost),
            currency=self.currency,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, comp: ResourceCompensation) -> "ResourceCompensationModel":
        return cls(
            resource_id=comp.resource_id,
            base_salary=_encrypt_amount(comp.base_salary),
            total_salary=_encrypt_amount(comp.total_salary),
            overhead=_encrypt_amount(comp.overhead),
            hourly_cost=_encrypt_amount(comp.hourly_cost),
            currency=comp.currency,
        )
