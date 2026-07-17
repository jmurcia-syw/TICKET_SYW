"""Cálculo de disponibilidad de un Recurso al momento de asignar un ticket (Fase 5, spec 020).

Función pura de dominio (Principio I) — sin imports de Flask/SQLAlchemy. El orden de evaluación
es fijo (FR-013): ausencia aprobada vigente > día festivo > horario laboral.
"""
from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from backend.domain.entities.calendar import Holiday, WorkScheduleSlot, AbsenceRequest, Availability
from backend.domain.entities.resource import Resource

# Horario laboral por defecto cuando el recurso no tiene franjas propias configuradas
# (research.md Decisión 3 / spec.md Assumptions): lunes a viernes, 08:00-17:00 local.
DEFAULT_WEEKDAYS = (0, 1, 2, 3, 4)
DEFAULT_START_TIME = time(8, 0)
DEFAULT_END_TIME = time(17, 0)


def _local_now(resource: Resource, now_utc: datetime) -> datetime:
    """Convierte `now_utc` a la hora local del recurso. Sin `timezone` configurado, se usa UTC
    tal cual (mejor aproximación disponible, no bloquea el cálculo de festivos/horario)."""
    if resource.timezone:
        try:
            return now_utc.astimezone(ZoneInfo(resource.timezone))
        except Exception:
            return now_utc
    return now_utc


def _has_holiday_today(holidays: list[Holiday], local_date: date) -> Optional[Holiday]:
    """Solo festivos `category == "oficial"` afectan disponibilidad (spec 021, FR-007) — un
    festivo `regional_religioso` es puramente informativo y nunca produce `reason: "holiday"`."""
    for h in holidays:
        if h.active and h.holiday_date == local_date and h.category == "oficial":
            return h
    return None


def _within_schedule(slots: list[WorkScheduleSlot], local_weekday: int, local_time: time) -> bool:
    if slots:
        return any(
            s.weekday == local_weekday and s.start_time <= local_time < s.end_time
            for s in slots
        )
    # Sin franjas propias: aplica el default (research.md Decisión 3).
    return local_weekday in DEFAULT_WEEKDAYS and DEFAULT_START_TIME <= local_time < DEFAULT_END_TIME


def _absence_covers_now(active_absence: AbsenceRequest, local_now: datetime) -> bool:
    """FR-017 (spec 022): una ausencia sin horas (`start_time`/`end_time` nulos) cubre el día
    completo, igual que antes; una ausencia parcial solo cuenta mientras la hora local esté
    dentro de `[start_time, end_time)` de ese día."""
    if active_absence.start_time is None or active_absence.end_time is None:
        return True
    return active_absence.start_time <= local_now.time() < active_absence.end_time


def compute_availability(
    resource: Resource,
    now_utc: datetime,
    holidays: list[Holiday],
    work_schedule_slots: list[WorkScheduleSlot],
    active_absence: Optional[AbsenceRequest],
) -> Availability:
    """Disponibilidad de `resource` en `now_utc` (FR-013 a FR-016; permisos parciales FR-017).

    `holidays` debe venir ya filtrado por el país del recurso (o vacío si no tiene país). Una
    ausencia aprobada (`active_absence`) siempre cuenta, incluso sin `timezone`/país configurados
    — es un dato explícito, no depende de la zona horaria del recurso. La hora local se calcula
    igual para la ausencia parcial y para festivo/horario, así que se resuelve una sola vez.
    """
    local_now = _local_now(resource, now_utc)

    if active_absence is not None and _absence_covers_now(active_absence, local_now):
        return Availability(
            available=False,
            reason="absence",
            detail=f"Ausencia aprobada del {active_absence.start_date.isoformat()} "
                   f"al {active_absence.end_date.isoformat()}",
        )

    # FR-016: sin timezone ni país configurados no hay forma de evaluar festivo/horario con
    # sentido — se trata como disponible por defecto, sin penalizar la falta de datos.
    if not resource.timezone and not resource.calendar_country:
        return Availability(available=True)

    local_date = local_now.date()
    local_time = local_now.time()

    holiday = _has_holiday_today(holidays, local_date) if resource.calendar_country else None
    if holiday is not None:
        return Availability(available=False, reason="holiday", detail=holiday.name)

    if not _within_schedule(work_schedule_slots, local_now.weekday(), local_time):
        return Availability(available=False, reason="outside_hours", detail="Fuera de horario laboral")

    return Availability(available=True)
