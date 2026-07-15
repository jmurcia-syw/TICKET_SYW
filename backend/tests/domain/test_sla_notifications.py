"""Detección de vencimientos de SLA (spec 014, Historia 3) — dominio puro, sin DB.

`sla_service.is_breach` es el predicado que usa la tarea periódica Celery
(`backend/workers/sla_tasks.py::check_sla_breaches`) para decidir a qué tickets notificar sin
volver a notificar uno que ya fue marcado `vencido`.
"""
from datetime import datetime, timedelta, timezone
import uuid

from backend.domain.entities.ticket import Ticket
from backend.domain.services import sla_service

NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)


def _ticket(**overrides) -> Ticket:
    defaults = dict(
        id=uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="high", severity="s2",
        client_id=uuid.uuid4(), created_by=uuid.uuid4(), status="en_ejecucion",
    )
    defaults.update(overrides)
    return Ticket(**defaults)


def test_is_breach_true_when_consumed_exceeds_limit_but_status_still_corriendo():
    ticket = _ticket(
        sla_status="corriendo", sla_phase="ejecucion", sla_phase_limit_minutes=60,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(hours=2),
    )
    assert sla_service.is_breach(ticket, NOW) is True


def test_is_breach_false_when_within_limit():
    ticket = _ticket(
        sla_status="corriendo", sla_phase="ejecucion", sla_phase_limit_minutes=60,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=10),
    )
    assert sla_service.is_breach(ticket, NOW) is False


def test_is_breach_false_when_already_marked_vencido():
    """No se debe re-notificar un ticket que la propia tarea ya marcó como vencido."""
    ticket = _ticket(
        sla_status="vencido", sla_phase="ejecucion", sla_phase_limit_minutes=60,
        sla_consumed_seconds=7200, sla_last_resume_at=NOW - timedelta(hours=2),
    )
    assert sla_service.is_breach(ticket, NOW) is False


def test_is_breach_false_when_paused():
    ticket = _ticket(
        sla_status="pausado", sla_phase="ejecucion", sla_phase_limit_minutes=60,
        sla_consumed_seconds=7200, sla_last_resume_at=None,
    )
    assert sla_service.is_breach(ticket, NOW) is False


def test_is_breach_false_when_no_sla():
    ticket = _ticket(sla_status="sin_sla", sla_phase=None, sla_phase_limit_minutes=None)
    assert sla_service.is_breach(ticket, NOW) is False
