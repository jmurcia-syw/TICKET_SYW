"""Reglas de negocio del registro diario de tiempos (Fase 2)."""
from datetime import date, timedelta
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
                               allow_any: bool) -> None:
        if allow_any:
            return
        assignee_ids = {a["assignee_id"] for a in tickets_repo.list_assignments(ticket.id)}
        if ticket.assignee_id:
            assignee_ids.add(str(ticket.assignee_id))
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

    # ── operaciones ──────────────────────────────────────────────────────────

    def create(self, *, resource_id: uuid.UUID, ticket, work_date: date, duration_minutes: int,
              created_by: uuid.UUID, work_sessions_repo, tickets_repo,
              note: Optional[str] = None, allow_any: bool = False) -> WorkSession:
        self.validate_duration(duration_minutes)
        self.validate_not_future(work_date)
        self.assert_ticket_ownership(resource_id, ticket, tickets_repo, allow_any)
        self.assert_ticket_open_or_admin(ticket, allow_any)
        self.assert_daily_limit(resource_id, work_date, duration_minutes, work_sessions_repo)
        work_session = WorkSession.create(
            resource_id=resource_id, ticket_id=ticket.id, work_date=work_date,
            duration_minutes=duration_minutes, created_by=created_by, note=note,
        )
        return work_sessions_repo.create(work_session)

    def update(self, *, existing: WorkSession, actor_id: uuid.UUID, work_sessions_repo,
              duration_minutes: Optional[int] = None, note: Optional[str] = None,
              allow_any: bool = False) -> WorkSession:
        self.assert_within_edit_window(existing.work_date, allow_any)
        new_duration = duration_minutes if duration_minutes is not None else existing.duration_minutes
        self.validate_duration(new_duration)
        self.assert_daily_limit(existing.resource_id, existing.work_date, new_duration,
                                work_sessions_repo, exclude_id=existing.id)
        return work_sessions_repo.update(
            existing.id, actor_id, duration_minutes=duration_minutes, note=note)

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
