"""Reglas de negocio del registro diario de tiempos (Fase 2 / Fase 2.1)."""
from datetime import date, datetime, timedelta
from typing import Optional
import uuid

from backend.domain.entities.work_session import WorkSession, MAX_DAILY_MINUTES, EDIT_WINDOW_DAYS
from backend.domain.errors import DomainError


class WorkSessionValidationError(DomainError):
    default_status_code = 400


class WorkSessionAuthorizationError(DomainError):
    default_status_code = 403


class WorkSessionConflictError(DomainError):
    default_status_code = 409


class WorkSessionService:
    # ── validaciones atómicas (reutilizadas por create/update) ──────────────

    def validate_duration(self, duration_minutes: int) -> None:
        if duration_minutes is None or duration_minutes <= 0:
            raise WorkSessionValidationError(
                "invalid_duration", "La duración debe ser mayor a 0 minutos")

    def validate_not_future(self, work_date: date) -> None:
        if work_date > date.today():
            raise WorkSessionValidationError(
                "future_date", "No se puede registrar tiempo con fecha futura")

    def assert_ticket_ownership(self, resource_id: uuid.UUID, ticket, tickets_repo,
                               allow_any: bool, is_task: bool = False,
                               resources_repo=None) -> None:
        if allow_any:
            return
        assignee_ids = {a["assignee_id"] for a in tickets_repo.list_assignments(ticket.id)}
        if ticket.assignee_id:
            assignee_ids.add(str(ticket.assignee_id))
        # spec 009 FR-001: el creador de una Tarea/Subtarea puede registrar tiempo aunque no sea
        # su `assignee_id` formal (p. ej. una Subtarea que él creó pero asignó a otro recurso) —
        # sin exigir el historial de asignaciones de Triage, que solo tiene sentido para Ticket.
        if is_task and resources_repo is not None:
            creator_resource = resources_repo.get_by_user_id(ticket.created_by)
            if creator_resource:
                assignee_ids.add(str(creator_resource.id))
        if str(resource_id) not in assignee_ids:
            raise WorkSessionAuthorizationError(
                "not_assigned", "El recurso no participa de este ticket")

    def assert_ticket_open_or_admin(self, ticket, allow_any: bool) -> None:
        if ticket.status == "cerrado" and not allow_any:
            raise WorkSessionConflictError(
                "ticket_closed", "No se puede registrar tiempo en un ticket cerrado")

    def assert_daily_limit(self, resource_id: uuid.UUID, work_date: date, duration_minutes: int,
                           work_sessions_repo, exclude_id: Optional[uuid.UUID] = None) -> None:
        current_total = work_sessions_repo.sum_minutes_for_day(resource_id, work_date, exclude_id=exclude_id)
        if current_total + duration_minutes > MAX_DAILY_MINUTES:
            raise WorkSessionValidationError(
                "daily_limit_exceeded",
                f"El total del día superaría las 24 horas (ya registrado: {current_total} min)",
                current_total_minutes=current_total,
            )

    def assert_within_edit_window(self, work_date: date, allow_any: bool) -> None:
        if allow_any:
            return
        if (date.today() - work_date).days > EDIT_WINDOW_DAYS:
            raise WorkSessionAuthorizationError(
                "edit_window_expired",
                f"La ventana de edición de {EDIT_WINDOW_DAYS} días para este registro ya expiró")

    def resolve_duration(self, *, started_at: Optional[datetime], ended_at: Optional[datetime],
                        duration_minutes: Optional[int]) -> int:
        """Calcula la duración desde hora de inicio/fin si ambas vienen presentes (ignorando
        cualquier duration_minutes explícito); si no, exige que venga la duración manual."""
        if started_at is None and ended_at is None:
            if duration_minutes is None:
                raise WorkSessionValidationError(
                    "invalid_duration",
                    "Debe indicar la duración, o la hora de inicio y de finalización")
            return duration_minutes
        if started_at is None or ended_at is None:
            raise WorkSessionValidationError(
                "incomplete_time_range",
                "Debe indicar tanto la hora de inicio como la de finalización")
        if ended_at <= started_at:
            raise WorkSessionValidationError(
                "invalid_time_range",
                "La hora de finalización debe ser posterior a la de inicio")
        return round((ended_at - started_at).total_seconds() / 60)

    # ── operaciones ──────────────────────────────────────────────────────────

    def create(self, *, resource_id: uuid.UUID, ticket, work_date: date,
              created_by: uuid.UUID, work_sessions_repo, tickets_repo,
              duration_minutes: Optional[int] = None, started_at: Optional[datetime] = None,
              ended_at: Optional[datetime] = None, note: Optional[str] = None,
              allow_any: bool = False, is_task: bool = False, resources_repo=None) -> WorkSession:
        resolved_duration = self.resolve_duration(
            started_at=started_at, ended_at=ended_at, duration_minutes=duration_minutes)
        self.validate_duration(resolved_duration)
        self.validate_not_future(work_date)
        self.assert_ticket_ownership(resource_id, ticket, tickets_repo, allow_any,
                                     is_task=is_task, resources_repo=resources_repo)
        self.assert_ticket_open_or_admin(ticket, allow_any)
        self.assert_daily_limit(resource_id, work_date, resolved_duration, work_sessions_repo)
        work_session = WorkSession.create(
            resource_id=resource_id, ticket_id=ticket.id, work_date=work_date,
            duration_minutes=resolved_duration, created_by=created_by, note=note,
            started_at=started_at, ended_at=ended_at,
        )
        return work_sessions_repo.create(work_session)

    def update(self, *, existing: WorkSession, actor_id: uuid.UUID, work_sessions_repo,
              duration_minutes: Optional[int] = None, note: Optional[str] = None,
              started_at: Optional[datetime] = None, ended_at: Optional[datetime] = None,
              allow_any: bool = False) -> WorkSession:
        self.assert_within_edit_window(existing.work_date, allow_any)
        if started_at is not None or ended_at is not None:
            new_started = started_at if started_at is not None else existing.started_at
            new_ended = ended_at if ended_at is not None else existing.ended_at
            new_duration = self.resolve_duration(
                started_at=new_started, ended_at=new_ended, duration_minutes=duration_minutes)
        else:
            new_duration = duration_minutes if duration_minutes is not None else existing.duration_minutes
            new_started = None
            new_ended = None
        self.validate_duration(new_duration)
        self.assert_daily_limit(existing.resource_id, existing.work_date, new_duration,
                                work_sessions_repo, exclude_id=existing.id)
        return work_sessions_repo.update(
            existing.id, actor_id, duration_minutes=new_duration, note=note,
            started_at=new_started, ended_at=new_ended)

    def delete(self, *, existing: WorkSession, actor_id: uuid.UUID, work_sessions_repo,
              allow_any: bool = False) -> None:
        self.assert_within_edit_window(existing.work_date, allow_any)
        work_sessions_repo.soft_delete(existing.id, actor_id)

    def get_daily_summary(self, *, resource_id: uuid.UUID, date_from: date, date_to: date,
                          work_sessions_repo) -> dict:
        """Resumen día a día de un recurso (US3) — completa los días sin registro (FR-011)."""
        rows = work_sessions_repo.aggregate_by_resource_and_day(resource_id, date_from, date_to)
        by_date = {r["work_date"]: r["total_minutes"] for r in rows}
        days = []
        current = date_from
        while current <= date_to:
            total = by_date.get(current, 0)
            days.append({"work_date": current, "total_minutes": total, "sin_registro": total == 0})
            current += timedelta(days=1)
        return {
            "resource_id": resource_id,
            "range": {"date_from": date_from, "date_to": date_to},
            "days": days,
            "total_minutes": sum(d["total_minutes"] for d in days),
        }

    def get_all_resources_summary(self, *, date_from: date, date_to: date, work_sessions_repo) -> list[dict]:
        """Overview por recurso (sin desglose diario) para Coordinador/QM/Admin sin
        un `resource_id` específico."""
        rows = work_sessions_repo.aggregate_by_resource_and_day(None, date_from, date_to)
        totals: dict[uuid.UUID, int] = {}
        for row in rows:
            totals[row["resource_id"]] = totals.get(row["resource_id"], 0) + row["total_minutes"]
        return [{"resource_id": rid, "total_minutes": minutes} for rid, minutes in totals.items()]
