"""Motor de dominio del SLA (Fase 4, spec 014; motor dinámico spec 022).

Resuelve la regla aplicable (Proyecto+Prioridad, sin fallback — research.md Decisión 3), calcula
el consumo/estado de la fase de SLA vigente, y deriva el efecto lateral de una transición de
estado FSM sobre el snapshot (data-model.md). Puro: sin imports de Flask/SQLAlchemy (Principio
II) — recibe entidades y repos ya resueltos, nunca toca la sesión de DB directamente.

FR-014 (clarificación 2026-07-14): este módulo NUNCA debe impedir una transición de FSM. Las
funciones de aquí son de solo cómputo — el llamador (backend/api/routes/tickets.py) decide qué
hacer si algo falla, pero nunca debe abortar la transición ya aplicada por ese fallo.

Spec 022 (Historia 2): `compute_available_seconds` reemplaza el reloj de pared puro por la suma
de los intervalos en los que el recurso asignado está realmente disponible (horario efectivo +
festivos + ausencias, incluidas las parciales por horas) — research.md Decisión 4. Los
parámetros nuevos de `compute_consumed_seconds`/`compute_state` son opcionales (default `None`):
sin ellos se preserva el wall-clock puro original, sin romper llamadores no migrados todavía.
"""
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from backend.domain.fsm.ticket_fsm import SLA_PHASE_FOR_STATE, STATE_COUNTS_FOR_SLA
from backend.domain.services.availability_service import (
    DEFAULT_END_TIME, DEFAULT_START_TIME, DEFAULT_WEEKDAYS,
)


def resolve_rule(project_id, priority: str, sla_rule_repo):
    """Búsqueda exacta (project_id, priority), sin fallback (FR-002)."""
    if project_id is None:
        return None
    return sla_rule_repo.find_by_project_priority(project_id, priority)


def initial_state(project_id, priority: str, sla_rule_repo, now: datetime) -> dict:
    """Estado de SLA inicial de un ticket recién creado (nace en estado `nuevo`, fase `contacto`).

    Solo debe invocarse para `record_type` == "Ticket" (FR-012) — el llamador es responsable de
    ese chequeo.
    """
    rule = resolve_rule(project_id, priority, sla_rule_repo)
    if rule is None:
        return {
            "sla_rule_id": None, "sla_phase": None, "sla_phase_limit_minutes": None,
            "sla_consumed_seconds": 0, "sla_last_resume_at": None, "sla_status": "sin_sla",
            "sla_contact_result": None, "sla_contact_consumed_seconds": None,
        }
    return {
        "sla_rule_id": rule.id, "sla_phase": "contacto",
        "sla_phase_limit_minutes": rule.contact_minutes,
        "sla_consumed_seconds": 0, "sla_last_resume_at": now, "sla_status": "corriendo",
        "sla_contact_result": None, "sla_contact_consumed_seconds": None,
    }


def _local_time_at(resource, dt: datetime) -> datetime:
    if resource and resource.timezone:
        try:
            return dt.astimezone(ZoneInfo(resource.timezone))
        except Exception:
            return dt
    return dt


def _day_available_intervals(resource, day: date, holidays: list, schedule_slots: list,
                             absences: list) -> list[tuple[time, time]]:
    """Intervalos `[start, end)` en hora local en los que `resource` está disponible ese `day`
    (spec 022, research.md Decisión 4) — mismo orden de prioridad que `availability_service`
    (ausencia > festivo > horario), pero a nivel de rango en vez de un solo instante."""
    if resource and resource.calendar_country:
        for h in holidays:
            if h.active and h.holiday_date == day and h.category == "oficial":
                return []

    if schedule_slots:
        slot = next((s for s in schedule_slots if s.weekday == day.weekday()), None)
        if slot is None:
            return []
        window = (slot.start_time, slot.end_time)
    elif day.weekday() in DEFAULT_WEEKDAYS:
        window = (DEFAULT_START_TIME, DEFAULT_END_TIME)
    else:
        return []

    intervals = [window]
    for absence in absences:
        if not (absence.start_date <= day <= absence.end_date):
            continue
        if absence.start_time is None or absence.end_time is None:
            return []  # Ausencia de día completo: nada disponible ese día.
        next_intervals: list[tuple[time, time]] = []
        for start, end in intervals:
            if absence.end_time <= start or absence.start_time >= end:
                next_intervals.append((start, end))
                continue
            if absence.start_time > start:
                next_intervals.append((start, absence.start_time))
            if absence.end_time < end:
                next_intervals.append((absence.end_time, end))
        intervals = next_intervals

    return intervals


def compute_available_seconds(resource, from_dt: datetime, to_dt: datetime,
                              holidays: list, schedule_slots: list, absences: list) -> int:
    """Segundos disponibles de `resource` entre `from_dt` y `to_dt` (spec 022, FR-006 a FR-010):
    solo cuentan los intervalos en los que `availability_service` habría devuelto
    `available=True` — horario efectivo (heredado o personalizado) + festivos oficiales +
    ausencias (incluidas las parciales por horas). Recorre día por día en la hora local del
    recurso; sin `timezone`/país configurados no hay forma de evaluar horario/festivo con
    sentido, así que se cuenta el rango completo como disponible (mismo fallback de FR-016)."""
    if to_dt <= from_dt:
        return 0
    if resource and not resource.timezone and not resource.calendar_country:
        return int((to_dt - from_dt).total_seconds())

    local_from = _local_time_at(resource, from_dt)
    local_to = _local_time_at(resource, to_dt)
    tzinfo = local_from.tzinfo

    total_seconds = 0
    day = local_from.date()
    last_day = local_to.date()
    while day <= last_day:
        for start, end in _day_available_intervals(resource, day, holidays, schedule_slots, absences):
            day_start_dt = datetime.combine(day, start, tzinfo=tzinfo)
            day_end_dt = datetime.combine(day, end, tzinfo=tzinfo)
            overlap_start = max(day_start_dt, local_from)
            overlap_end = min(day_end_dt, local_to)
            if overlap_end > overlap_start:
                total_seconds += int((overlap_end - overlap_start).total_seconds())
        day += timedelta(days=1)
    return total_seconds


def compute_consumed_seconds(ticket, now: datetime, resource=None, holidays: list | None = None,
                             schedule_slots: list | None = None, absences: list | None = None) -> int:
    consumed = ticket.sla_consumed_seconds or 0
    if ticket.sla_last_resume_at:
        if resource is not None:
            consumed += compute_available_seconds(
                resource, ticket.sla_last_resume_at, now,
                holidays or [], schedule_slots or [], absences or [])
        else:
            consumed += int((now - ticket.sla_last_resume_at).total_seconds())
    return consumed


def _availability_reason_now(resource, now: datetime, holidays: list | None,
                             schedule_slots: list | None, absences: list | None) -> Optional[str]:
    """`None` si `resource` está disponible en `now`, o el motivo (`"absence"` | `"holiday"` |
    `"outside_hours"`) si no — misma precedencia que `availability_service.compute_availability`
    (ausencia > festivo > horario, FR-013), evaluada a un solo instante en vez de un rango."""
    if not resource.timezone and not resource.calendar_country:
        return None  # FR-016: sin datos para evaluar, se asume disponible.

    local_now = _local_time_at(resource, now)
    local_date = local_now.date()
    local_time = local_now.time()

    for absence in (absences or []):
        if absence.start_date <= local_date <= absence.end_date:
            if absence.start_time is None or absence.start_time <= local_time < absence.end_time:
                return "absence"

    if resource.calendar_country:
        for h in (holidays or []):
            if h.active and h.holiday_date == local_date and h.category == "oficial":
                return "holiday"

    if schedule_slots:
        slot = next((s for s in schedule_slots if s.weekday == local_date.weekday()), None)
        if slot and slot.start_time <= local_time < slot.end_time:
            return None
        return "outside_hours"
    if local_date.weekday() in DEFAULT_WEEKDAYS and DEFAULT_START_TIME <= local_time < DEFAULT_END_TIME:
        return None
    return "outside_hours"


def compute_state(ticket, now: datetime, resource=None, holidays: list | None = None,
                  schedule_slots: list | None = None, absences: list | None = None) -> dict:
    """Estado de SLA derivado en el momento de lectura (cálculo perezoso, research.md Decisión 2)
    — no persiste nada, solo refresca lo que se muestra (detalle/listado de tickets).

    `resource`/`holidays`/`schedule_slots`/`absences` (spec 022, opcionales): cuando el llamador
    los resuelve, el consumo usa el motor dinámico (research.md Decisión 10) y, si el ticket
    está en fase activa pero el recurso no está disponible *en este instante*, el estado
    mostrado se anota como `"pausado"` con el motivo correspondiente en `pause_reason`
    (research.md Decisión 6) en vez de mostrar `"corriendo"` de forma engañosa — sin alterar el
    `sla_status` persistido ni sus valores posibles. Sin estos parámetros, se preserva el
    wall-clock puro original y `pause_reason` solo distingue la pausa por estado del ticket."""
    if ticket.sla_phase is None:
        return {
            "phase": None, "status": "sin_sla", "phase_limit_minutes": None,
            "consumed_seconds": 0, "rule_id": None,
            "contact_result": ticket.sla_contact_result, "contact_consumed_seconds": None,
            "pause_reason": None,
        }
    consumed = compute_consumed_seconds(ticket, now, resource, holidays, schedule_slots, absences)
    pause_reason: Optional[str] = None
    if ticket.sla_phase == "cerrado":
        status = "detenido"
    elif ticket.sla_phase_limit_minutes and consumed >= ticket.sla_phase_limit_minutes * 60:
        status = "vencido"
    elif ticket.sla_last_resume_at is None:
        status = "pausado"
        pause_reason = "ticket_status"
    else:
        reason = _availability_reason_now(resource, now, holidays, schedule_slots, absences) if resource is not None else None
        if reason is not None:
            status = "pausado"
            pause_reason = reason
        else:
            status = "corriendo"
    return {
        "phase": ticket.sla_phase, "status": status,
        "phase_limit_minutes": ticket.sla_phase_limit_minutes,
        "consumed_seconds": consumed,
        "rule_id": str(ticket.sla_rule_id) if ticket.sla_rule_id else None,
        "contact_result": ticket.sla_contact_result,
        "contact_consumed_seconds": ticket.sla_contact_consumed_seconds,
        "pause_reason": pause_reason,
    }


def apply_transition(ticket, new_status: str, now: datetime, sla_rule_repo) -> Optional[dict]:
    """Efecto lateral de una transición de estado FSM sobre el snapshot de SLA vigente
    (FR-004b/FR-005/FR-006). Devuelve un dict de columnas `sla_*` a persistir, o `None` si el
    ticket no tiene SLA configurado (nada que actualizar).
    """
    if ticket.sla_rule_id is None and ticket.sla_phase is None:
        return None

    consumed = compute_consumed_seconds(ticket, now)
    previous_phase = ticket.sla_phase

    if new_status == "pendiente_usuario":
        # Pausa (FR-005): mantiene la fase vigente, deja de correr.
        return {"sla_consumed_seconds": consumed, "sla_last_resume_at": None, "sla_status": "pausado"}

    if new_status in ("resuelto", "cerrado", "cancelado"):
        # Detiene definitivamente el cómputo (FR-006). `resuelto` puede reabrirse
        # (reject_resolution) — ver rama de reanudación más abajo.
        return {"sla_consumed_seconds": consumed, "sla_last_resume_at": None,
                "sla_phase": "cerrado", "sla_status": "detenido"}

    new_phase = SLA_PHASE_FOR_STATE.get(new_status)

    if previous_phase == "contacto" and new_phase == "ejecucion":
        # Cierre de la fase Contacto (FR-004b): se congela su resultado y la fase de
        # Ejecución arranca en cero con su propio tiempo límite — no hereda el consumo previo.
        rule = sla_rule_repo.get_by_id(ticket.sla_rule_id) if ticket.sla_rule_id else None
        contact_limit = ticket.sla_phase_limit_minutes
        contact_result = "vencido" if (contact_limit and consumed >= contact_limit * 60) else "cumplido"
        execution_limit = rule.execution_minutes if rule else None
        return {
            "sla_contact_result": contact_result,
            "sla_contact_consumed_seconds": consumed,
            "sla_phase": "ejecucion",
            "sla_phase_limit_minutes": execution_limit,
            "sla_consumed_seconds": 0,
            "sla_last_resume_at": now,
            "sla_status": "corriendo" if execution_limit else "sin_sla",
        }

    if STATE_COUNTS_FOR_SLA.get(new_status, False):
        # Reanudación (pendiente_usuario -> activo, o reapertura desde `resuelto` vía
        # reject_resolution) u otro estado activo de la misma fase: no se reinicia el consumo,
        # solo se retoma el conteo desde donde estaba.
        resumed_phase = new_phase or previous_phase or "ejecucion"
        limit = ticket.sla_phase_limit_minutes
        status = "vencido" if (limit and consumed >= limit * 60) else "corriendo"
        return {"sla_phase": resumed_phase, "sla_consumed_seconds": consumed,
                "sla_last_resume_at": now, "sla_status": status}

    return None


def is_breach(ticket, now: datetime, resource=None, holidays: list | None = None,
             schedule_slots: list | None = None, absences: list | None = None) -> bool:
    """True si la fase de SLA vigente ya superó su tiempo límite en tiempo real, pero el
    snapshot persistido (`sla_status`) todavía no lo refleja como `vencido` — candidato a
    notificación de vencimiento (Historia 3, FR-010). Usado por la tarea periódica
    `check_sla_breaches` (`backend/workers/sla_tasks.py`) para decidir a qué tickets notificar
    sin notificar dos veces al mismo ticket. Parámetros opcionales (spec 022, research.md
    Decisión 10): con ellos, el consumo usa el motor dinámico en vez de wall-clock puro."""
    if ticket.sla_status != "corriendo" or ticket.sla_phase_limit_minutes is None:
        return False
    consumed = compute_consumed_seconds(ticket, now, resource, holidays, schedule_slots, absences)
    return consumed >= ticket.sla_phase_limit_minutes * 60


def recalc_rule_for_project_or_priority_change(ticket, project_id, priority: str, now: datetime,
                                               sla_rule_repo) -> Optional[dict]:
    """FR-011: re-resuelve la regla aplicable a la fase vigente cuando cambia Proyecto o
    Prioridad, conservando el tiempo ya consumido en esa fase antes del cambio."""
    if ticket.sla_phase in (None, "cerrado"):
        return None
    consumed = compute_consumed_seconds(ticket, now)
    was_running = ticket.sla_last_resume_at is not None
    updates: dict = {"sla_consumed_seconds": consumed}
    if was_running:
        updates["sla_last_resume_at"] = now

    rule = resolve_rule(project_id, priority, sla_rule_repo)
    if rule is None:
        updates.update({"sla_rule_id": None, "sla_phase_limit_minutes": None, "sla_status": "sin_sla"})
        return updates

    limit = rule.contact_minutes if ticket.sla_phase == "contacto" else rule.execution_minutes
    updates.update({
        "sla_rule_id": rule.id, "sla_phase_limit_minutes": limit,
        "sla_status": "vencido" if consumed >= limit * 60 else ("corriendo" if was_running else "pausado"),
    })
    return updates
