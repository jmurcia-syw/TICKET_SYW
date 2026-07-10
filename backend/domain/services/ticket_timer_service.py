"""Reglas de negocio del cronómetro manual de tiempo (spec 012, provisional).

`finish()` reutiliza `WorkSessionService.create()` tal cual — mismas validaciones (ticket
cerrado, participación del recurso, límite diario) que la carga manual de tiempo (spec 004);
ver research.md Decisión 4. Este módulo no modifica `work_session_service.py`.
"""
from datetime import date, datetime, timezone
from typing import Optional
import uuid

from backend.domain.entities.ticket_timer import TicketTimer
from backend.domain.entities.work_session import WorkSession
from backend.domain.errors import DomainError
from backend.domain.services.work_session_service import WorkSessionService

MIN_FINISH_SECONDS = 60
STALE_THRESHOLD_SECONDS = 12 * 60 * 60  # referencia inicial: 12 horas (FR-010, research.md Decisión 5)


class TicketTimerConflictError(DomainError):
    default_status_code = 409


class TicketTimerNotFoundError(DomainError):
    default_status_code = 404


class TicketTimerService:
    def __init__(self, work_session_service: Optional[WorkSessionService] = None) -> None:
        self._work_sessions = work_session_service or WorkSessionService()

    def start(self, *, resource_id: uuid.UUID, ticket, timer_repo, tickets_repo,
              is_task: bool = False, resources_repo=None, now: Optional[datetime] = None) -> TicketTimer:
        now = now or datetime.now(timezone.utc)
        # Mismo chequeo de participación que la carga manual (FR-005/FR-006 de spec 004),
        # reutilizado tal cual — nunca `allow_any` (el cronómetro no tiene variante "para otro
        # recurso").
        self._work_sessions.assert_ticket_ownership(
            resource_id, ticket, tickets_repo, allow_any=False, is_task=is_task,
            resources_repo=resources_repo)

        current = timer_repo.get_by_resource(resource_id)
        if current.status != "inactive":
            raise TicketTimerConflictError(
                "timer_already_active",
                "Ya hay un cronómetro activo en otro ticket; termínalo o pausalo antes de iniciar uno nuevo",
                ticket_id=str(current.ticket_id))

        new_timer = TicketTimer(
            resource_id=resource_id, ticket_id=ticket.id, status="running",
            accumulated_seconds=0, started_at=now)
        return timer_repo.save(new_timer)

    def pause(self, *, resource_id: uuid.UUID, timer_repo, now: Optional[datetime] = None) -> TicketTimer:
        now = now or datetime.now(timezone.utc)
        current = timer_repo.get_by_resource(resource_id)
        if current.status != "running":
            raise TicketTimerConflictError(
                "no_active_timer", "No hay un cronómetro corriendo para pausar")
        current.accumulated_seconds = current.total_seconds(now)
        current.started_at = None
        current.status = "paused"
        return timer_repo.save(current)

    def resume(self, *, resource_id: uuid.UUID, timer_repo, now: Optional[datetime] = None) -> TicketTimer:
        now = now or datetime.now(timezone.utc)
        current = timer_repo.get_by_resource(resource_id)
        if current.status != "paused":
            raise TicketTimerConflictError(
                "no_paused_timer", "No hay un cronómetro pausado para reanudar")
        current.status = "running"
        current.started_at = now
        return timer_repo.save(current)

    def finish(self, *, resource_id: uuid.UUID, created_by: uuid.UUID, timer_repo, tickets_repo,
              work_sessions_repo, note: Optional[str] = None, is_task: bool = False,
              resources_repo=None, now: Optional[datetime] = None) -> WorkSession:
        now = now or datetime.now(timezone.utc)
        current = timer_repo.get_by_resource(resource_id)
        if current.status not in ("running", "paused"):
            raise TicketTimerNotFoundError(
                "no_active_timer", "No hay un cronómetro activo para este recurso")

        total = current.total_seconds(now)
        if total < MIN_FINISH_SECONDS:
            raise TicketTimerConflictError(
                "duration_too_short", "El cronómetro acumuló menos de un minuto")

        ticket = tickets_repo.get_by_id(current.ticket_id)
        if ticket is None:
            raise TicketTimerNotFoundError(
                "ticket_not_found", "El ticket del cronómetro ya no existe")
        duration_minutes = max(1, round(total / 60))

        # Delega en WorkSessionService.create() tal cual: si el ticket está cerrado o se supera
        # el límite diario, propaga el mismo DomainError que la carga manual (mismo código y
        # status) y el cronómetro NO se resetea (permite reintentar sin perder el progreso).
        work_session = self._work_sessions.create(
            resource_id=resource_id, ticket=ticket, work_date=date.today(),
            duration_minutes=duration_minutes, created_by=created_by,
            work_sessions_repo=work_sessions_repo, tickets_repo=tickets_repo,
            note=note, allow_any=False, is_task=is_task, resources_repo=resources_repo,
        )

        timer_repo.save(TicketTimer(resource_id=resource_id))  # vuelve a inactive
        return work_session
