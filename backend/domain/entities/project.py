from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import uuid


@dataclass
class Project:
    id: uuid.UUID
    client_id: uuid.UUID
    name: str
    start_date: date
    description: Optional[str] = None
    overview: Optional[str] = None
    sale_services_usd: Optional[float] = None
    sale_licenses_usd: Optional[float] = None
    sale_subscriptions_usd: Optional[float] = None
    components_sold: Optional[str] = None
    active: bool = True
    end_date_estimated: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, client_id: uuid.UUID, name: str, start_date: date, **kwargs) -> "Project":
        return cls(id=uuid.uuid4(), client_id=client_id, name=name, start_date=start_date, **kwargs)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()
