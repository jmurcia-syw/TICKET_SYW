"""Reasignación de resolutor (spec 023) — dominio puro, sin DB."""
import uuid

import pytest

from backend.domain.entities.resource import Resource, Skill
from backend.domain.entities.ticket import Ticket
from backend.domain.services.reassignment_service import ReassignmentError, ReassignmentService


def _ticket(**overrides) -> Ticket:
    defaults = dict(
        id=uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="high", severity="s2",
        client_id=uuid.uuid4(), created_by=uuid.uuid4(), status="en_analisis",
        assignee_id=uuid.uuid4(),
    )
    defaults.update(overrides)
    return Ticket(**defaults)


def _resource(**overrides) -> Resource:
    defaults = dict(id=uuid.uuid4(), full_name="Resolutor", email="r@sywork.net")
    defaults.update(overrides)
    return Resource(**defaults)


def test_validate_ok_returns_no_missing_skills_when_new_resource_has_them():
    skill = Skill.create("JDE_GL", "JDE GL")
    ticket = _ticket(skills=[skill])
    new_assignee = _resource(skills=[skill])
    missing = ReassignmentService().validate(ticket, new_assignee)
    assert missing == []


def test_validate_returns_missing_skills_but_does_not_block():
    required = Skill.create("ORACLE_FUSION", "Oracle Fusion")
    ticket = _ticket(skills=[required])
    new_assignee = _resource(skills=[])
    missing = ReassignmentService().validate(ticket, new_assignee)
    assert missing == ["ORACLE_FUSION"]


def test_validate_rejects_missing_resource():
    ticket = _ticket()
    with pytest.raises(ReassignmentError) as exc:
        ReassignmentService().validate(ticket, None)
    assert exc.value.status_code == 404


def test_validate_rejects_inactive_resource():
    ticket = _ticket()
    with pytest.raises(ReassignmentError) as exc:
        ReassignmentService().validate(ticket, _resource(active=False))
    assert exc.value.code == "resource_inactive"


def test_validate_rejects_terminal_ticket_status():
    ticket = _ticket(status="cerrado")
    with pytest.raises(ReassignmentError) as exc:
        ReassignmentService().validate(ticket, _resource())
    assert exc.value.status_code == 409
    assert exc.value.code == "ticket_closed"


def test_validate_rejects_same_assignee():
    assignee_id = uuid.uuid4()
    ticket = _ticket(assignee_id=assignee_id)
    with pytest.raises(ReassignmentError) as exc:
        ReassignmentService().validate(ticket, _resource(id=assignee_id))
    assert exc.value.code == "validation_error"
