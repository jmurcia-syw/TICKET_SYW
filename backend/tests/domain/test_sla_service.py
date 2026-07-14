"""Motor de dominio del SLA (spec 014, Historia 2) — dominio puro, sin DB."""
from datetime import datetime, timedelta, timezone
import uuid

import pytest

from backend.domain.entities.sla_rule import SlaRule
from backend.domain.entities.ticket import Ticket
from backend.domain.services import sla_service


def _ticket(**overrides) -> Ticket:
    defaults = dict(
        id=uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="high", severity="s2",
        client_id=uuid.uuid4(), created_by=uuid.uuid4(), status="nuevo",
    )
    defaults.update(overrides)
    return Ticket(**defaults)


class _FakeSlaRuleRepo:
    def __init__(self, rules: dict):
        self._rules = rules  # (project_id, priority) -> SlaRule

    def find_by_project_priority(self, project_id, priority):
        return self._rules.get((project_id, priority))

    def get_by_id(self, rule_id):
        for rule in self._rules.values():
            if rule.id == rule_id:
                return rule
        return None


def _rule(project_id=None, priority="high", contact=15, execution=480) -> SlaRule:
    return SlaRule.create(project_id or uuid.uuid4(), priority, contact, execution)


NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)


# ── resolve_rule / initial_state ─────────────────────────────────────────────

def test_resolve_rule_no_project_returns_none():
    repo = _FakeSlaRuleRepo({})
    assert sla_service.resolve_rule(None, "high", repo) is None


def test_initial_state_without_rule_is_sin_sla():
    repo = _FakeSlaRuleRepo({})
    state = sla_service.initial_state(uuid.uuid4(), "high", repo, NOW)
    assert state["sla_status"] == "sin_sla"
    assert state["sla_phase"] is None
    assert state["sla_rule_id"] is None


def test_initial_state_with_rule_starts_contacto_running():
    project_id = uuid.uuid4()
    rule = _rule(project_id, "high", contact=15, execution=480)
    repo = _FakeSlaRuleRepo({(project_id, "high"): rule})
    state = sla_service.initial_state(project_id, "high", repo, NOW)
    assert state["sla_phase"] == "contacto"
    assert state["sla_phase_limit_minutes"] == 15
    assert state["sla_status"] == "corriendo"
    assert state["sla_last_resume_at"] == NOW
    assert state["sla_consumed_seconds"] == 0


# ── apply_transition: fase Contacto -> Ejecución ─────────────────────────────

def test_transition_contacto_to_ejecucion_freezes_contact_result_and_resets_consumed():
    project_id = uuid.uuid4()
    rule = _rule(project_id, "high", contact=15, execution=480)
    repo = _FakeSlaRuleRepo({(project_id, "high"): rule})
    ticket = _ticket(
        project_id=project_id, priority="high", status="pre_analisis",
        sla_rule_id=rule.id, sla_phase="contacto", sla_phase_limit_minutes=15,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=5), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "contacto", NOW, repo)
    assert updates["sla_phase"] == "ejecucion"
    assert updates["sla_contact_result"] == "cumplido"  # 5 min < 15 min límite
    assert updates["sla_contact_consumed_seconds"] == 300
    assert updates["sla_consumed_seconds"] == 0
    assert updates["sla_phase_limit_minutes"] == 480
    assert updates["sla_status"] == "corriendo"


def test_transition_contacto_to_ejecucion_marks_contact_vencido_if_over_limit():
    project_id = uuid.uuid4()
    rule = _rule(project_id, "high", contact=15, execution=480)
    repo = _FakeSlaRuleRepo({(project_id, "high"): rule})
    ticket = _ticket(
        project_id=project_id, priority="high", status="pre_analisis",
        sla_rule_id=rule.id, sla_phase="contacto", sla_phase_limit_minutes=15,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=20), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "contacto", NOW, repo)
    assert updates["sla_contact_result"] == "vencido"


# ── apply_transition: pausa / reanudación ────────────────────────────────────

def test_transition_to_pendiente_usuario_pauses_without_losing_consumed():
    ticket = _ticket(
        status="en_ejecucion", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=600, sla_last_resume_at=NOW - timedelta(minutes=10), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "pendiente_usuario", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_status"] == "pausado"
    assert updates["sla_last_resume_at"] is None
    assert updates["sla_consumed_seconds"] == 1200  # 600 + 10min


def test_transition_resume_from_pendiente_usuario_keeps_accumulated_time():
    ticket = _ticket(
        status="pendiente_usuario", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=1200, sla_last_resume_at=None, sla_status="pausado",
    )
    updates = sla_service.apply_transition(ticket, "en_ejecucion", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "ejecucion"
    assert updates["sla_consumed_seconds"] == 1200  # no se reinicia
    assert updates["sla_last_resume_at"] == NOW
    assert updates["sla_status"] == "corriendo"


# ── apply_transition: estados finales ────────────────────────────────────────

def test_transition_to_cerrado_stops_and_freezes():
    ticket = _ticket(
        status="resuelto", sla_phase="cerrado", sla_phase_limit_minutes=480,
        sla_consumed_seconds=1000, sla_last_resume_at=None, sla_status="detenido",
    )
    updates = sla_service.apply_transition(ticket, "cerrado", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "cerrado"
    assert updates["sla_status"] == "detenido"
    assert updates["sla_last_resume_at"] is None


def test_transition_reopen_from_resuelto_resumes_ejecucion_phase():
    """reject_resolution: resuelto -> en_ejecucion. sla_phase quedó en 'cerrado' al llegar a
    resuelto; debe recuperar 'ejecucion' y seguir sumando desde el consumo ya acumulado."""
    ticket = _ticket(
        status="resuelto", sla_phase="cerrado", sla_phase_limit_minutes=480,
        sla_consumed_seconds=2000, sla_last_resume_at=None, sla_status="detenido",
    )
    updates = sla_service.apply_transition(ticket, "en_ejecucion", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "ejecucion"
    assert updates["sla_consumed_seconds"] == 2000
    assert updates["sla_last_resume_at"] == NOW


def test_transition_no_op_when_no_sla_configured():
    ticket = _ticket(status="nuevo", sla_phase=None, sla_rule_id=None)
    updates = sla_service.apply_transition(ticket, "pre_analisis", NOW, _FakeSlaRuleRepo({}))
    assert updates is None


# ── compute_state (cálculo perezoso, solo lectura) ───────────────────────────

def test_compute_state_sin_sla():
    ticket = _ticket(sla_phase=None, sla_rule_id=None)
    state = sla_service.compute_state(ticket, NOW)
    assert state["status"] == "sin_sla"
    assert state["phase"] is None


def test_compute_state_vencido():
    ticket = _ticket(
        sla_phase="ejecucion", sla_phase_limit_minutes=60,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(hours=2), sla_status="corriendo",
    )
    state = sla_service.compute_state(ticket, NOW)
    assert state["status"] == "vencido"
    assert state["consumed_seconds"] == 7200


# ── recalc_rule_for_project_or_priority_change (FR-011) ──────────────────────

def test_recalc_on_project_change_preserves_consumed_and_applies_new_rule():
    old_project, new_project = uuid.uuid4(), uuid.uuid4()
    new_rule = _rule(new_project, "high", contact=15, execution=960)
    repo = _FakeSlaRuleRepo({(new_project, "high"): new_rule})
    ticket = _ticket(
        project_id=old_project, priority="high", status="en_ejecucion",
        sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=100, sla_last_resume_at=NOW - timedelta(minutes=10), sla_status="corriendo",
    )
    updates = sla_service.recalc_rule_for_project_or_priority_change(
        ticket, new_project, "high", NOW, repo)
    assert updates["sla_rule_id"] == new_rule.id
    assert updates["sla_phase_limit_minutes"] == 960
    assert updates["sla_consumed_seconds"] == 700  # 100 + 600s ya transcurridos, preservado
    assert updates["sla_last_resume_at"] == NOW


def test_recalc_to_project_without_rule_marks_sin_sla():
    old_project, new_project = uuid.uuid4(), uuid.uuid4()
    repo = _FakeSlaRuleRepo({})
    ticket = _ticket(
        project_id=old_project, priority="high", status="en_ejecucion",
        sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=100, sla_last_resume_at=NOW - timedelta(minutes=10), sla_status="corriendo",
    )
    updates = sla_service.recalc_rule_for_project_or_priority_change(
        ticket, new_project, "high", NOW, repo)
    assert updates["sla_rule_id"] is None
    assert updates["sla_status"] == "sin_sla"


def test_recalc_noop_when_no_active_phase():
    ticket = _ticket(sla_phase=None, sla_rule_id=None)
    updates = sla_service.recalc_rule_for_project_or_priority_change(
        ticket, uuid.uuid4(), "high", NOW, _FakeSlaRuleRepo({}))
    assert updates is None
