"""Motor de dominio del SLA (Fase 4, spec 014).

Resuelve la regla aplicable (Proyecto+Prioridad, sin fallback — research.md Decisión 3), calcula
el consumo/estado de la fase de SLA vigente, y deriva el efecto lateral de una transición de
estado FSM sobre el snapshot (data-model.md). Puro: sin imports de Flask/SQLAlchemy (Principio
II) — recibe entidades y repos ya resueltos, nunca toca la sesión de DB directamente.

FR-014 (clarificación 2026-07-14): este módulo NUNCA debe impedir una transición de FSM. Las
funciones de aquí son de solo cómputo — el llamador (backend/api/routes/tickets.py) decide qué
hacer si algo falla, pero nunca debe abortar la transición ya aplicada por ese fallo.
"""
from datetime import datetime
from typing import Optional

from backend.domain.fsm.ticket_fsm import SLA_PHASE_FOR_STATE, STATE_COUNTS_FOR_SLA


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


def compute_consumed_seconds(ticket, now: datetime) -> int:
    consumed = ticket.sla_consumed_seconds or 0
    if ticket.sla_last_resume_at:
        consumed += int((now - ticket.sla_last_resume_at).total_seconds())
    return consumed


def compute_state(ticket, now: datetime) -> dict:
    """Estado de SLA derivado en el momento de lectura (cálculo perezoso, research.md Decisión 2)
    — no persiste nada, solo refresca lo que se muestra (detalle/listado de tickets)."""
    if ticket.sla_phase is None:
        return {
            "phase": None, "status": "sin_sla", "phase_limit_minutes": None,
            "consumed_seconds": 0, "rule_id": None,
            "contact_result": ticket.sla_contact_result, "contact_consumed_seconds": None,
        }
    consumed = compute_consumed_seconds(ticket, now)
    if ticket.sla_phase == "cerrado":
        status = "detenido"
    elif ticket.sla_phase_limit_minutes and consumed >= ticket.sla_phase_limit_minutes * 60:
        status = "vencido"
    elif ticket.sla_last_resume_at is not None:
        status = "corriendo"
    else:
        status = "pausado"
    return {
        "phase": ticket.sla_phase, "status": status,
        "phase_limit_minutes": ticket.sla_phase_limit_minutes,
        "consumed_seconds": consumed,
        "rule_id": str(ticket.sla_rule_id) if ticket.sla_rule_id else None,
        "contact_result": ticket.sla_contact_result,
        "contact_consumed_seconds": ticket.sla_contact_consumed_seconds,
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


def is_breach(ticket, now: datetime) -> bool:
    """True si la fase de SLA vigente ya superó su tiempo límite en tiempo real, pero el
    snapshot persistido (`sla_status`) todavía no lo refleja como `vencido` — candidato a
    notificación de vencimiento (Historia 3, FR-010). Usado por la tarea periódica
    `check_sla_breaches` (`backend/workers/sla_tasks.py`) para decidir a qué tickets notificar
    sin notificar dos veces al mismo ticket."""
    if ticket.sla_status != "corriendo" or ticket.sla_phase_limit_minutes is None:
        return False
    consumed = compute_consumed_seconds(ticket, now)
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
