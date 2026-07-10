from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

TIMER_STATUSES = ("inactive", "running", "paused")


@dataclass
class TicketTimer:
    resource_id: uuid.UUID
    ticket_id: Optional[uuid.UUID] = None
    status: str = "inactive"
    accumulated_seconds: int = 0
    started_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def total_seconds(self, now: datetime) -> int:
        """Tiempo acumulado total en el ciclo actual (research.md Decisión 2)."""
        if self.status == "running" and self.started_at is not None:
            return self.accumulated_seconds + int((now - self.started_at).total_seconds())
        return self.accumulated_seconds

    def running_seconds(self, now: datetime) -> int:
        """Tiempo corriendo sin interrupción desde el último inicio/reanudación (FR-010)."""
        if self.status == "running" and self.started_at is not None:
            return int((now - self.started_at).total_seconds())
        return 0
