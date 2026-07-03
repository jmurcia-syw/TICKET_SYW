"""Generación de notificaciones internas (FR-023/024)."""
import uuid

from backend.domain.entities.notification import Notification
from backend.domain.entities.ticket import format_ticket_number

_MESSAGES = {
    "assigned": "Se te asignó el ticket {number}: {title}",
    "user_replied": "El usuario respondió en el ticket {number}",
    "resolution_rejected": "El usuario rechazó la resolución del ticket {number}",
    "closed": "El ticket {number} fue cerrado",
    "close_eligible": "El ticket {number} lleva 3+ días resuelto sin respuesta del usuario; puedes cerrarlo",
}


class NotificationService:
    def build(self, user_id: uuid.UUID, event_type: str, ticket_id: uuid.UUID,
              ticket_number: int, title: str = "") -> Notification:
        template = _MESSAGES[event_type]
        message = template.format(number=format_ticket_number(ticket_number), title=title)
        return Notification.create(user_id=user_id, event_type=event_type,
                                   ticket_id=ticket_id, message=message)
