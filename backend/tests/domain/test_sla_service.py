"""Motor de dominio del SLA (spec 014, Historia 2) — dominio puro, sin DB."""
from datetime import datetime, time, timedelta, timezone
import uuid

import pytest

from backend.domain.entities.calendar import WorkScheduleSlot
from backend.domain.entities.resource import Resource
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


# ── apply_transition: fase Contacto -> Ejecución (spec 038 US2: Contacto corre hasta
# `en_analisis`, ya no se congela al asignar/entrar a `contacto` — research.md Decisión 3) ────

def test_transition_to_contacto_keeps_contact_phase_running_not_frozen():
    """El reloj de Contacto sigue corriendo al asignar (entrar al estado FSM `contacto`) — se
    congela recién al pasar a `en_analisis` (spec 038 FR-009/FR-010), no en este punto."""
    project_id = uuid.uuid4()
    rule = _rule(project_id, "high", contact=15, execution=480)
    repo = _FakeSlaRuleRepo({(project_id, "high"): rule})
    ticket = _ticket(
        project_id=project_id, priority="high", status="pre_analisis",
        sla_rule_id=rule.id, sla_phase="contacto", sla_phase_limit_minutes=15,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=5), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "contacto", NOW, repo)
    assert updates["sla_phase"] == "contacto"
    assert updates["sla_status"] == "corriendo"
    assert updates["sla_consumed_seconds"] == 300  # sigue sumando, no se reinicia ni congela
    assert "sla_contact_result" not in updates


def test_transition_contacto_to_en_analisis_freezes_contact_result_and_resets_consumed():
    project_id = uuid.uuid4()
    rule = _rule(project_id, "high", contact=15, execution=480)
    repo = _FakeSlaRuleRepo({(project_id, "high"): rule})
    ticket = _ticket(
        project_id=project_id, priority="high", status="contacto",
        sla_rule_id=rule.id, sla_phase="contacto", sla_phase_limit_minutes=15,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=5), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "en_analisis", NOW, repo)
    assert updates["sla_phase"] == "ejecucion"
    assert updates["sla_contact_result"] == "cumplido"  # 5 min < 15 min límite
    assert updates["sla_contact_consumed_seconds"] == 300
    assert updates["sla_consumed_seconds"] == 0
    assert updates["sla_phase_limit_minutes"] == 480
    assert updates["sla_status"] == "corriendo"


def test_transition_contacto_to_en_analisis_marks_contact_vencido_if_over_limit():
    project_id = uuid.uuid4()
    rule = _rule(project_id, "high", contact=15, execution=480)
    repo = _FakeSlaRuleRepo({(project_id, "high"): rule})
    ticket = _ticket(
        project_id=project_id, priority="high", status="contacto",
        sla_rule_id=rule.id, sla_phase="contacto", sla_phase_limit_minutes=15,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=20), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "en_analisis", NOW, repo)
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


def test_transition_to_resuelto_keeps_execution_phase_running_not_frozen():
    """spec 038 US2 (FR-011): el SLA de Resolución sigue corriendo mientras el ticket permanece
    en `resuelto` — ya no se congela ahí (reemplaza el congelamiento de OBS-0059/spec 033)."""
    ticket = _ticket(
        status="en_pruebas", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=100), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "resuelto", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "ejecucion"
    assert updates["sla_status"] == "corriendo"
    assert updates["sla_consumed_seconds"] == 6000  # sigue sumando, no se congela
    assert "sla_execution_result" not in updates


def test_transition_to_cerrado_freezes_execution_result_cumplido():
    """OBS-0059 (spec 033) reubicado a `cerrado` (spec 038 US2 FR-012): se congela recién ahí,
    con el ticket ya en `resuelto` (fase `ejecucion` sigue corriendo hasta este punto)."""
    ticket = _ticket(
        status="resuelto", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=100), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "cerrado", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "cerrado"
    assert updates["sla_execution_result"] == "cumplido"  # 100 min < 480 min límite
    assert updates["sla_execution_consumed_seconds"] == 6000


def test_transition_to_cerrado_marks_execution_vencido_if_over_limit():
    ticket = _ticket(
        status="resuelto", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=500), sla_status="vencido",
    )
    updates = sla_service.apply_transition(ticket, "cerrado", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_execution_result"] == "vencido"


def test_reject_resolution_from_resuelto_keeps_consumed_without_reset():
    """spec 038 US2 (FR-013): rechazar la resolución (`resuelto` -> `en_ejecucion`) no reinicia
    el tiempo de SLA de Resolución ya consumido — nunca se congeló al entrar a `resuelto`."""
    ticket = _ticket(
        status="resuelto", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=6000, sla_last_resume_at=NOW - timedelta(minutes=10), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "en_ejecucion", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "ejecucion"
    assert updates["sla_consumed_seconds"] == 6600  # 6000 + 10 min, sin reinicio
    assert updates["sla_status"] == "corriendo"


def test_transition_to_cancelado_from_contacto_leaves_execution_result_none():
    """Si el ticket se cancela sin haber llegado nunca a la fase Ejecución, no aplica
    sla_execution_result (queda ausente del dict, no se sobre-escribe con un valor falso)."""
    ticket = _ticket(
        status="nuevo", sla_phase="contacto", sla_phase_limit_minutes=15,
        sla_consumed_seconds=0, sla_last_resume_at=NOW - timedelta(minutes=5), sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "cancelado", NOW, _FakeSlaRuleRepo({}))
    assert updates["sla_phase"] == "cerrado"
    assert "sla_execution_result" not in updates


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


# ── apply_transition con calendario (spec 028, OBS-0038/OBS-0039) ───────────

_RESOURCE_ID = uuid.uuid4()
_SLOTS = [WorkScheduleSlot.create(_RESOURCE_ID, weekday=d, start_time=time(8, 0), end_time=time(17, 0))
         for d in range(5)]  # lunes a viernes, 08:00-17:00


def _resource(**overrides) -> Resource:
    defaults = dict(id=_RESOURCE_ID, full_name="Resolutor", email="r@sywork.net",
                    timezone="UTC", calendar_country="CO")
    defaults.update(overrides)
    return Resource(**defaults)


def test_transition_with_resource_consumes_calendar_time_not_wall_clock():
    """OBS-0038: cambiar de estado no debe inflar el consumo con tiempo fuera de horario. Miércoles
    16:00 (dentro de jornada) -> jueves 09:05: real disponible = 1h (mié 16-17h) + 1h05 (jue 8-9:05)
    = 7500s, muy por debajo de las ~17h05 (61500s) de wall-clock puro que se calculaba antes."""
    resource = _resource()
    last_resume = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)  # miércoles
    now = datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc)  # jueves
    ticket = _ticket(
        status="en_ejecucion", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=0, sla_last_resume_at=last_resume, sla_status="corriendo",
    )
    updates = sla_service.apply_transition(
        ticket, "pendiente_usuario", now, _FakeSlaRuleRepo({}),
        resource=resource, schedule_slots=_SLOTS, holidays=[], absences=[])
    assert updates["sla_consumed_seconds"] == 7500
    assert updates["sla_consumed_seconds"] < int((now - last_resume).total_seconds())


def test_transition_without_resource_keeps_wall_clock_fallback():
    """Sin resource (parámetros opcionales, spec 022/028 Decisión 10): se preserva el
    comportamiento wall-clock original — no rompe llamadores no migrados."""
    last_resume = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
    now = datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc)
    ticket = _ticket(
        status="en_ejecucion", sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=0, sla_last_resume_at=last_resume, sla_status="corriendo",
    )
    updates = sla_service.apply_transition(ticket, "pendiente_usuario", now, _FakeSlaRuleRepo({}))
    assert updates["sla_consumed_seconds"] == int((now - last_resume).total_seconds())


# ── next_work_period_start (spec 028, FR-005/OBS-0040) ───────────────────────

def test_next_work_period_start_delays_ticket_created_outside_hours():
    """Un ticket creado fuera de horario (miércoles 23:00) debe mostrar como inicio de jornada
    el jueves 08:00, no la hora de creación."""
    resource = _resource()
    created_at = datetime(2026, 7, 15, 23, 0, tzinfo=timezone.utc)  # miércoles 23:00
    start = sla_service.next_work_period_start(resource, created_at, [], _SLOTS, [])
    assert start == datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc)  # jueves 08:00


def test_next_work_period_start_within_hours_returns_same_instant():
    resource = _resource()
    created_at = datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc)  # miércoles, ya en jornada
    start = sla_service.next_work_period_start(resource, created_at, [], _SLOTS, [])
    assert start == created_at


def test_next_work_period_start_without_resource_returns_input_unchanged():
    created_at = datetime(2026, 7, 15, 23, 0, tzinfo=timezone.utc)
    assert sla_service.next_work_period_start(None, created_at) == created_at


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


# ── compute_transition_compliance (spec 023, Historial de estados) ──────────

def _transition(from_status: str, to_status: str, created_at: datetime) -> dict:
    return {
        "id": str(uuid.uuid4()), "from_status": from_status, "to_status": to_status,
        "actor_id": str(uuid.uuid4()), "comment_id": None, "created_at": created_at.isoformat(),
    }


def test_transition_compliance_first_row_has_no_elapsed_or_sla():
    ticket = _ticket(sla_rule_id=uuid.uuid4())
    result = sla_service.compute_transition_compliance(
        ticket, [_transition("nuevo", "pre_analisis", NOW)])
    assert result[0]["elapsed_seconds"] is None
    assert result[0]["sla_phase_closed"] is None
    assert result[0]["sla_met"] is None


def test_transition_compliance_closes_contacto_cumplido():
    ticket = _ticket(sla_rule_id=uuid.uuid4(), sla_contact_result="cumplido")
    transitions = [
        _transition("nuevo", "pre_analisis", NOW),
        _transition("pre_analisis", "contacto", NOW + timedelta(minutes=10)),
    ]
    result = sla_service.compute_transition_compliance(ticket, transitions)
    closing = result[1]
    assert closing["sla_phase_closed"] == "contacto"
    assert closing["sla_met"] is True
    assert closing["elapsed_seconds"] == 600


def test_transition_compliance_closes_contacto_vencido():
    ticket = _ticket(sla_rule_id=uuid.uuid4(), sla_contact_result="vencido")
    transitions = [
        _transition("nuevo", "pre_analisis", NOW),
        _transition("pre_analisis", "contacto", NOW + timedelta(minutes=20)),
    ]
    result = sla_service.compute_transition_compliance(ticket, transitions)
    assert result[1]["sla_met"] is False


def test_transition_compliance_internal_transition_is_neutral():
    ticket = _ticket(sla_rule_id=uuid.uuid4(), sla_contact_result="cumplido")
    transitions = [
        _transition("nuevo", "pre_analisis", NOW),
        _transition("pre_analisis", "contacto", NOW + timedelta(minutes=10)),
        _transition("contacto", "en_analisis", NOW + timedelta(minutes=20)),
    ]
    result = sla_service.compute_transition_compliance(ticket, transitions)
    internal = result[2]
    assert internal["sla_phase_closed"] is None
    assert internal["sla_met"] is None
    assert internal["elapsed_seconds"] == 600


def test_transition_compliance_closes_ejecucion_on_last_transition_when_stopped():
    ticket = _ticket(
        sla_rule_id=uuid.uuid4(), sla_contact_result="cumplido",
        sla_phase="cerrado", sla_phase_limit_minutes=480,
        sla_consumed_seconds=100, sla_status="detenido",
    )
    transitions = [
        _transition("contacto", "en_ejecucion", NOW),
        _transition("en_ejecucion", "resuelto", NOW + timedelta(minutes=5)),
    ]
    result = sla_service.compute_transition_compliance(ticket, transitions)
    closing = result[1]
    assert closing["sla_phase_closed"] == "ejecucion"
    assert closing["sla_met"] is True  # 100s consumidos < 480min de límite


def test_transition_compliance_without_sla_rule_is_all_neutral():
    ticket = _ticket(sla_rule_id=None)
    transitions = [
        _transition("nuevo", "pre_analisis", NOW),
        _transition("pre_analisis", "contacto", NOW + timedelta(minutes=10)),
    ]
    result = sla_service.compute_transition_compliance(ticket, transitions)
    assert all(r["sla_phase_closed"] is None and r["sla_met"] is None for r in result)
