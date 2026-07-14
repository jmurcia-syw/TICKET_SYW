"""Tarea periódica de detección de vencimientos de SLA (Fase 4, spec 014, Historia 3).

`check_sla_breaches` corre cada 5 minutos (ver `beat_schedule` en `celery_app.py`): busca tickets
con la fase de SLA vigente corriendo, evalúa en tiempo real si ya superaron su límite
(`sla_service.is_breach`, dominio puro) y, para los que sí, marca `sla_status='vencido'` y notifica
al Resolutor/encargado asignado y a los `ProjectMember` con rol Coordinador del proyecto del
ticket (clarificación 2026-07-14, FR-010) — reutiliza `notification_service.py`, sin canal nuevo.

Capa de infraestructura (usa DB/repos) — la lógica de decisión vive en
`backend/domain/services/sla_service.py` (dominio puro).
"""
from datetime import datetime, timezone
import logging
import uuid

from backend.domain.services import sla_service
from backend.domain.services.notification_service import NotificationService
from backend.infra.database import close_db, get_db
from backend.infra.repositories.notification_repo import NotificationRepository
from backend.infra.repositories.project_member_repo import ProjectMemberRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.ticket_repo import TicketRepository
from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
_notif_svc = NotificationService()


@celery_app.task(name="backend.workers.sla_tasks.check_sla_breaches")
def check_sla_breaches() -> int:
    """Devuelve la cantidad de tickets marcados como vencidos y notificados en esta corrida."""
    db = get_db()
    try:
        now = datetime.now(timezone.utc)
        ticket_repo = TicketRepository(db)
        notif_repo = NotificationRepository(db)
        member_repo = ProjectMemberRepository(db)
        resource_repo = ResourceRepository(db)

        breached_count = 0
        for ticket in ticket_repo.list_active_sla_running():
            if not sla_service.is_breach(ticket, now):
                continue
            ticket_repo.update_fields(ticket.id, sla_status="vencido")

            recipients: set[uuid.UUID] = set()
            if ticket.assignee_id:
                assignee = resource_repo.get_by_id(ticket.assignee_id)
                if assignee and assignee.user_id:
                    recipients.add(assignee.user_id)
            if ticket.project_id:
                for member in member_repo.list_by_project(ticket.project_id, role_name="Coordinador"):
                    recipients.add(uuid.UUID(member["user_id"]))

            for user_id in recipients:
                notif_repo.add(
                    _notif_svc.build(user_id, "sla_breached", ticket.id, ticket.ticket_number),
                    commit=False,
                )
            db.commit()
            breached_count += 1

        return breached_count
    except Exception:
        logger.exception("check_sla_breaches failed")
        db.rollback()
        raise
    finally:
        close_db()
