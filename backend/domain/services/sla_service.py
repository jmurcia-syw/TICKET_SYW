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
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from backend.domain.fsm.ticket_fsm import SLA_PHASE_FOR_STATE, STATE_COUNTS_FOR_SLA
from backend.domain.services.availability_service import (
    DEFAULT_END_TIME, DEFAULT_START_TIME, DEFAULT_WEEKDAYS,
)

logger = logging.getLogger(__name__)


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
            logger.exception(
                "No se pudo resolver timezone '%s' del recurso %s; se usa la hora sin convertir",
                resource.timezone, resource.id,
            )
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


_WORK_PERIOD_SEARCH_LIMIT_DAYS = 30


def next_work_period_start(resource, from_dt: datetime, holidays: list | None = None,
                           schedule_slots: list | None = None,
                           absences: list | None = None) -> datetime:
    """Inicio de la próxima jornada laboral disponible de `resource` en o después de `from_dt`
    (spec 028, FR-005/OBS-0040) — "inicio de la jornada laboral aplicable" a mostrar en el
    detalle del ticket. Si `from_dt` ya cae dentro de un intervalo disponible, devuelve el
    inicio de ESE intervalo (no `from_dt`); reutiliza `_day_available_intervals`, mismo criterio
    de disponibilidad que `compute_available_seconds`. Sin timezone/país configurados, o si no
    se encuentra ningún intervalo disponible dentro de `_WORK_PERIOD_SEARCH_LIMIT_DAYS`, devuelve
    `from_dt` sin modificar (mismo fallback de FR-016)."""
    if resource is None or (not resource.timezone and not resource.calendar_country):
        return from_dt

    local_from = _local_time_at(resource, from_dt)
    tzinfo = local_from.tzinfo
    day = local_from.date()
    for _ in range(_WORK_PERIOD_SEARCH_LIMIT_DAYS):
        for start, end in _day_available_intervals(resource, day, holidays or [],
                                                    schedule_slots or [], absences or []):
            interval_start = datetime.combine(day, start, tzinfo=tzinfo)
            interval_end = datetime.combine(day, end, tzinfo=tzinfo)
            if interval_end > local_from:
                candidate = max(interval_start, local_from)
                return candidate.astimezone(timezone.utc)
        day += timedelta(days=1)
    return from_dt


def resource_local_now(resource, now: Optional[datetime] = None) -> datetime:
    """Instante actual convertido al huso horario de `resource` (spec 028, US6/OBS-0036) — evita
    fijar `work_date` a la fecha del servidor (Docker corre en UTC) cuando el recurso está en
    otro huso y registra tiempo cerca de medianoche local. Sin `resource`/`timezone`, devuelve
    `now` sin convertir (mismo fallback de FR-016)."""
    return _local_time_at(resource, now or datetime.now(timezone.utc))


def is_off_hours(resource, work_date: date, holidays: list | None = None,
                 schedule_slots: list | None = None, absences: list | None = None,
                 started_at: Optional[datetime] = None, ended_at: Optional[datetime] = None) -> bool:
    """Clasifica un registro de tiempo como "fuera de jornada" (spec 028, US6/OBS-0036, FR-020):
    `True` si el intervalo `[started_at, ended_at]` cae total o parcialmente fuera del horario
    disponible del recurso, o -sin horas explícitas- si `work_date` completo no tiene ningún
    intervalo disponible (fin de semana/feriado/ausencia de día completo). Nunca bloquea el
    registro (FR-020/FR-021), es puramente informativo. Sin timezone/país configurados no hay
    forma de evaluar (FR-016): se asume dentro de jornada."""
    if resource is None or (not resource.timezone and not resource.calendar_country):
        return False
    holidays = holidays or []
    schedule_slots = schedule_slots or []
    absences = absences or []
    if started_at is not None and ended_at is not None:
        total = (ended_at - started_at).total_seconds()
        if total <= 0:
            return False
        available = compute_available_seconds(resource, started_at, ended_at, holidays, schedule_slots, absences)
        return available < total
    return not _day_available_intervals(resource, work_date, holidays, schedule_slots, absences)


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
            "execution_result": ticket.sla_execution_result, "execution_consumed_seconds": None,
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
        "execution_result": ticket.sla_execution_result,
        "execution_consumed_seconds": ticket.sla_execution_consumed_seconds,
        "pause_reason": pause_reason,
    }


def apply_transition(ticket, new_status: str, now: datetime, sla_rule_repo, resource=None,
                     holidays: list | None = None, schedule_slots: list | None = None,
                     absences: list | None = None) -> Optional[dict]:
    """Efecto lateral de una transición de estado FSM sobre el snapshot de SLA vigente
    (FR-004b/FR-005/FR-006). Devuelve un dict de columnas `sla_*` a persistir, o `None` si el
    ticket no tiene SLA configurado (nada que actualizar).

    `resource`/`holidays`/`schedule_slots`/`absences` (spec 022/028, opcionales, mismo criterio
    que `compute_state`): sin ellos, el consumo que esta función congela/persiste cae a
    wall-clock puro, igual que antes de spec 028 — con ellos, usa el motor dinámico de
    disponibilidad (`compute_available_seconds`), cerrando el hallazgo OBS-0038/OBS-0039 (el
    snapshot persistido por una transición de estado quedaba desalineado del wall-clock-consciente
    que ya usaba `compute_state` en la lectura).
    """
    if ticket.sla_rule_id is None and ticket.sla_phase is None:
        return None

    consumed = compute_consumed_seconds(ticket, now, resource, holidays, schedule_slots, absences)
    previous_phase = ticket.sla_phase

    if new_status == "pendiente_usuario":
        # Pausa (FR-005): mantiene la fase vigente, deja de correr.
        return {"sla_consumed_seconds": consumed, "sla_last_resume_at": None, "sla_status": "pausado"}

    if new_status in ("cerrado", "cancelado"):
        # Detiene definitivamente el cómputo (FR-006; acotado spec 038 US2 FR-011/FR-012 — ya no
        # incluye `resuelto`, donde el SLA de Resolución debe seguir corriendo hasta `cerrado`).
        # `resuelto` reanuda su conteo sin reiniciar vía la rama `STATE_COUNTS_FOR_SLA` más abajo.
        updates = {"sla_consumed_seconds": consumed, "sla_last_resume_at": None,
                   "sla_phase": "cerrado", "sla_status": "detenido"}
        if previous_phase == "ejecucion":
            # OBS-0059 (spec 033): análogo al cierre de Contacto (FR-004b) — se congela el
            # resultado de la fase Ejecución si llegó a correr. Si el ticket se cerró/canceló
            # todavía en fase Contacto (nunca llegó a Ejecución), queda en None (no aplica).
            execution_limit = ticket.sla_phase_limit_minutes
            updates["sla_execution_result"] = (
                "vencido" if (execution_limit and consumed >= execution_limit * 60) else "cumplido")
            updates["sla_execution_consumed_seconds"] = consumed
        return updates

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


def compute_transition_compliance(ticket, transitions: list[dict], resource=None,
                                  holidays: list | None = None, schedule_slots: list | None = None,
                                  absences: list | None = None) -> list[dict]:
    """Enriquece el Historial de Estados (spec 023, FR-001/FR-002/FR-003) con, por transición:
    `elapsed_seconds` (tiempo disponible transcurrido desde la transición anterior — mismo motor
    que `compute_available_seconds`, spec 022), `sla_phase_closed` (fase de SLA que esa
    transición cierra, o `None`) y `sla_met` (cumplimiento de esa fase, o `None` si la transición
    no cierra una fase o no hay datos confiables para evaluarla).

    Solo se anota `sla_met` en las dos transiciones que efectivamente cierran una fase de SLA
    (entrar a `contacto` cierra Contacto; entrar a `resuelto`/`cerrado`/`cancelado` cierra
    Ejecución — ver `ticket_fsm.SLA_PHASE_FOR_STATE` y research.md spec 023 Decisión 1), y solo
    cuando el dato ya persistido es confiable: `sla_contact_result` para Contacto, y el snapshot
    final `sla_consumed_seconds`/`sla_phase_limit_minutes` para Ejecución (solo en la última
    transición, con el ticket ya detenido — ciclos de reapertura no se re-evalúan, ayuda de UI,
    no auditoría). No muta `transitions`; devuelve una lista nueva. Puro (Capa 1): sin DB.
    """
    if not transitions:
        return []
    last_index = len(transitions) - 1
    enriched: list[dict] = []
    previous_dt: Optional[datetime] = None
    for i, t in enumerate(transitions):
        created_at = datetime.fromisoformat(t["created_at"])
        elapsed_seconds = None
        if previous_dt is not None:
            elapsed_seconds = compute_available_seconds(
                resource, previous_dt, created_at, holidays or [], schedule_slots or [], absences or [])

        sla_phase_closed = None
        sla_met = None
        if ticket.sla_rule_id is not None:
            if t["to_status"] == "contacto":
                sla_phase_closed = "contacto"
                if ticket.sla_contact_result in ("cumplido", "vencido"):
                    sla_met = ticket.sla_contact_result == "cumplido"
            elif (t["to_status"] in ("resuelto", "cerrado", "cancelado") and i == last_index
                  and ticket.sla_status == "detenido" and ticket.sla_phase_limit_minutes):
                sla_phase_closed = "ejecucion"
                sla_met = ticket.sla_consumed_seconds < ticket.sla_phase_limit_minutes * 60

        enriched.append({**t, "elapsed_seconds": elapsed_seconds,
                         "sla_phase_closed": sla_phase_closed, "sla_met": sla_met})
        previous_dt = created_at
    return enriched


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
