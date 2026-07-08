import uuid
from datetime import date, timedelta

import pytest

from backend.domain.services.work_session_service import (
    WorkSessionService, WorkSessionValidationError, WorkSessionAuthorizationError,
    WorkSessionConflictError,
)


class FakeTicket:
    def __init__(self, ticket_id=None, assignee_id=None, status="contacto"):
        self.id = ticket_id or uuid.uuid4()
        self.assignee_id = assignee_id
        self.status = status


class FakeTicketsRepo:
    def __init__(self, assignments=None):
        self._assignments = assignments or []

    def list_assignments(self, ticket_id):
        return self._assignments


class FakeWorkSessionsRepo:
    def __init__(self, existing_minutes=0):
        self._existing_minutes = existing_minutes
        self.created = None

    def sum_minutes_for_day(self, resource_id, work_date, exclude_id=None):
        return self._existing_minutes

    def create(self, work_session):
        self.created = work_session
        return work_session


@pytest.fixture()
def svc():
    return WorkSessionService()


def test_create_happy_path(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    repo = FakeWorkSessionsRepo()
    ws = svc.create(
        resource_id=resource_id, ticket=ticket, work_date=date.today(), duration_minutes=90,
        created_by=uuid.uuid4(), work_sessions_repo=repo, tickets_repo=FakeTicketsRepo(), note="ok",
    )
    assert repo.created is ws
    assert ws.duration_minutes == 90


def test_create_rejects_ticket_not_assigned_to_resource(svc):
    ticket = FakeTicket(assignee_id=uuid.uuid4())
    with pytest.raises(WorkSessionAuthorizationError) as exc:
        svc.create(
            resource_id=uuid.uuid4(), ticket=ticket, work_date=date.today(), duration_minutes=60,
            created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(),
        )
    assert exc.value.code == "not_assigned"
    assert exc.value.status_code == 403


def test_create_allows_historic_assignment(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=uuid.uuid4())  # reasignado a otro recurso
    assignments = [{"assignee_id": str(resource_id)}]
    ws = svc.create(
        resource_id=resource_id, ticket=ticket, work_date=date.today(), duration_minutes=30,
        created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
        tickets_repo=FakeTicketsRepo(assignments=assignments),
    )
    assert ws.duration_minutes == 30


def test_create_allow_any_bypasses_ownership_and_closed_ticket(svc):
    ticket = FakeTicket(assignee_id=uuid.uuid4(), status="cerrado")
    ws = svc.create(
        resource_id=uuid.uuid4(), ticket=ticket, work_date=date.today(), duration_minutes=15,
        created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
        tickets_repo=FakeTicketsRepo(), allow_any=True,
    )
    assert ws.duration_minutes == 15


def test_create_rejects_closed_ticket_without_allow_any(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id, status="cerrado")
    with pytest.raises(WorkSessionConflictError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date.today(), duration_minutes=15,
            created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(),
        )
    assert exc.value.code == "ticket_closed"
    assert exc.value.status_code == 409


def test_create_rejects_future_date(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date.today() + timedelta(days=1),
            duration_minutes=30, created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(),
        )
    assert exc.value.code == "future_date"


@pytest.mark.parametrize("duration", [0, -10])
def test_create_rejects_zero_or_negative_duration(svc, duration):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date.today(), duration_minutes=duration,
            created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(),
        )
    assert exc.value.code == "invalid_duration"


def test_create_rejects_when_daily_limit_exceeded(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    repo = FakeWorkSessionsRepo(existing_minutes=1400)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date.today(), duration_minutes=100,
            created_by=uuid.uuid4(), work_sessions_repo=repo, tickets_repo=FakeTicketsRepo(),
        )
    assert exc.value.code == "daily_limit_exceeded"
    assert exc.value.status_code == 400
    assert exc.value.extra["current_total_minutes"] == 1400
