from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class ResourceCompensation:
    """Area protegida de compensacion del recurso (FR-032, SDD V3).

    Relacion 1..1 con Resource. Los montos se cifran en reposo (Capa 2);
    aqui viven en claro solo dentro del proceso.
    """
    resource_id: uuid.UUID
    base_salary: Optional[float] = None
    total_salary: Optional[float] = None
    overhead: Optional[float] = None
    hourly_cost: Optional[float] = None
    currency: str = "USD"
    updated_at: datetime = field(default_factory=datetime.utcnow)
