import uuid

from sqlalchemy.orm import Session

from backend.domain.entities.ticket_timer import TicketTimer
from backend.infra.models.ticket_timer_model import TicketTimerModel


class TicketTimerRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_resource(self, resource_id: uuid.UUID) -> TicketTimer:
        """Devuelve el cronómetro del recurso, o uno transitorio `inactive` (sin persistir) si
        todavía no existe fila — evita tener que aprovisionar una fila vacía por adelantado."""
        model = self._db.get(TicketTimerModel, resource_id)
        if model is None:
            return TicketTimer(resource_id=resource_id)
        return model.to_entity()

    def save(self, timer: TicketTimer) -> TicketTimer:
        """Upsert por `resource_id` (PK) — una sola fila por recurso (data-model.md)."""
        model = self._db.get(TicketTimerModel, timer.resource_id)
        if model is None:
            model = TicketTimerModel.from_entity(timer)
            self._db.add(model)
        else:
            model.ticket_id = timer.ticket_id
            model.status = timer.status
            model.accumulated_seconds = timer.accumulated_seconds
            model.started_at = timer.started_at
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()
