"""Reglas de negocio del cronómetro manual de tiempo (spec 012, provisional).

`finish()` reutiliza `WorkSessionService.create()` tal cual — mismas validaciones (ticket
cerrado, participación del recurso, límite diario) que la carga manual de tiempo (spec 004);
ver research.md Decisión 4. Este módulo no modifica `work_session_service.py`.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from backend.domain.entities.ticket_timer import TicketTimer
from backend.domain.entities.work_session import WorkSession
from backend.domain.errors import DomainError
from backend.domain.services import sla_service
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
        # OBS-0035 (spec 028): antes solo `finish()` (vía `WorkSessionService.create`) rechazaba
        # un ticket cerrado — permitía iniciar (e incluso pausar) un cronómetro sobre un ticket
        # ya finalizado, que recién fallaba confusamente al intentar terminarlo. Se adelanta el
        # mismo chequeo a `start()`.
        self._work_sessions.assert_ticket_open_or_admin(ticket, allow_any=False)

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
              resources_repo=None, now: Optional[datetime] = None,
              calendar_context: Optional[dict] = None) -> WorkSession:
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

        # OBS-0036 (spec 028): antes fijaba `work_date=date.today()` (fecha del servidor, UTC)
        # — si el recurso está en un huso detrás de UTC y termina cerca de medianoche local, el
        # servidor ya había cruzado al día siguiente. `calendar_context["resource"]` (resuelto
        # por el llamador, igual que `_resolve_sla_context`) da el huso real del recurso; sin
        # contexto, se conserva el fallback anterior (fecha UTC del servidor).
        resource = (calendar_context or {}).get("resource")
        work_date = sla_service.resource_local_now(resource, now).date() if resource else now.date()

        # Delega en WorkSessionService.create() tal cual: si el ticket está cerrado o se supera
        # el límite diario, propaga el mismo DomainError que la carga manual (mismo código y
        # status) y el cronómetro NO se resetea (permite reintentar sin perder el progreso).
        work_session = self._work_sessions.create(
            resource_id=resource_id, ticket=ticket, work_date=work_date,
            duration_minutes=duration_minutes, created_by=created_by,
            work_sessions_repo=work_sessions_repo, tickets_repo=tickets_repo,
            note=note, allow_any=False, is_task=is_task, resources_repo=resources_repo,
            **(calendar_context or {}),
        )

        timer_repo.save(TicketTimer(resource_id=resource_id))  # vuelve a inactive
        return work_session

    def stop_if_active_for_ticket(self, *, ticket, timer_repo, tickets_repo, work_sessions_repo,
                                  created_by: uuid.UUID, resources_repo=None, is_task: bool = False,
                                  now: Optional[datetime] = None,
                                  calendar_context: Optional[dict] = None) -> Optional[WorkSession]:
        """OBS-0035 (spec 028): efecto lateral al cerrar `ticket` — detiene automáticamente el
        cronómetro del recurso asignado si estaba corriendo/pausado sobre este mismo ticket,
        conservando el tiempo ya acumulado. El llamador (`backend/api/routes/tickets.py`) DEBE
        invocar esto antes de persistir el nuevo `status` como `"cerrado"`, para que `finish()`
        (vía `WorkSessionService.create`) todavía vea el ticket en su estado previo y no lo
        rechace como "ticket_closed". Si el tiempo acumulado es menor a `MIN_FINISH_SECONDS`, se
        descarta silenciosamente (cronómetro vuelve a `inactive`, sin crear `WorkSession`) — el
        cierre del ticket nunca debe bloquearse por esto."""
        if ticket.assignee_id is None:
            return None
        now = now or datetime.now(timezone.utc)
        current = timer_repo.get_by_resource(ticket.assignee_id)
        if current.status not in ("running", "paused") or current.ticket_id != ticket.id:
            return None
        if current.total_seconds(now) < MIN_FINISH_SECONDS:
            timer_repo.save(TicketTimer(resource_id=ticket.assignee_id))
            return None
        # spec 038 US4 (FR-020): `note` pasó a ser obligatoria en `WorkSessionService.create()` —
        # este efecto lateral automático no tiene un texto de usuario que ofrecer, así que usa
        # una descripción fija en su lugar (no puede pedirle nota a nadie: se dispara al cerrar
        # el ticket, no al detener el cronómetro manualmente).
        return self.finish(
            resource_id=ticket.assignee_id, created_by=created_by, timer_repo=timer_repo,
            tickets_repo=tickets_repo, work_sessions_repo=work_sessions_repo,
            note="Tiempo registrado automáticamente al cerrar el ticket con el cronómetro activo",
            is_task=is_task, resources_repo=resources_repo, now=now,
            calendar_context=calendar_context,
        )
