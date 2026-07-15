from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

# Reutiliza el catálogo de prioridades ya existente (backend/domain/entities/ticket.py) —
# corresponde a la columna "Severidad" de docs/SLAv1.xlsx.
PRIORITIES = ("critical", "high", "medium", "low")

SLA_STATUSES = ("sin_sla", "corriendo", "pausado", "vencido", "detenido")
SLA_PHASES = ("contacto", "ejecucion", "cerrado")
SLA_CONTACT_RESULTS = ("pendiente", "cumplido", "vencido")


@dataclass
class SlaRule:
    """Regla de tiempos límite de SLA por Proyecto + Prioridad (spec 014, FR-001/FR-002).

    No hay reglas de respaldo (fallback): cada combinación (project_id, priority) es
    independiente y editable — ver research.md Decisión 3, revisada 2026-07-14.
    """
    id: uuid.UUID
    project_id: uuid.UUID
    priority: str
    contact_minutes: int
    execution_minutes: int
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, project_id: uuid.UUID, priority: str, contact_minutes: int,
               execution_minutes: int) -> "SlaRule":
        return cls(id=uuid.uuid4(), project_id=project_id, priority=priority,
                   contact_minutes=contact_minutes, execution_minutes=execution_minutes)
