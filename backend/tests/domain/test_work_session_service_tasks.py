"""spec 009, US1 (FR-001/FR-002) — el creador de una Tarea/Subtarea puede registrar tiempo
aunque no sea su `assignee_id` formal; sin regresión para Ticket."""
import uuid
from datetime import date

import pytest

from backend.domain.services.work_session_service import (
    WorkSessionService, WorkSessionAuthorizationError,
)


class FakeTicket:
    def __init__(self, ticket_id=None, assignee_id=None, created_by=None, status="nuevo"):
        self.id = ticket_id or uuid.uuid4()
        self.assignee_id = assignee_id
        self.created_by = created_by or uuid.uuid4()
        self.status = status


class FakeTicketsRepo:
    def __init__(self, assignments=None):
        self._assignments = assignments or []

    def list_assignments(self, ticket_id):
        return self._assignments


class FakeResource:
    def __init__(self, resource_id):
        self.id = resource_id


class FakeResourcesRepo:
    def __init__(self, by_user: dict[uuid.UUID, uuid.UUID] | None = None):
        self._by_user = by_user or {}

    def get_by_user_id(self, user_id):
        resource_id = self._by_user.get(user_id)
        return FakeResource(resource_id) if resource_id else None


class FakeWorkSessionsRepo:
    def sum_minutes_for_day(self, resource_id, work_date, exclude_id=None):
        return 0

    def create(self, work_session):
        return work_session


@pytest.fixture()
def svc():
    return WorkSessionService()


def test_creator_of_task_can_register_time_even_if_not_assignee(svc):
    creator_user_id = uuid.uuid4()
    creator_resource_id = uuid.uuid4()
    other_assignee_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=other_assignee_id, created_by=creator_user_id)
    resources_repo = FakeResourcesRepo({creator_user_id: creator_resource_id})

    ws = svc.create(
        resource_id=creator_resource_id, ticket=ticket, work_date=date.today(),
        duration_minutes=30, created_by=creator_user_id,
        work_sessions_repo=FakeWorkSessionsRepo(), tickets_repo=FakeTicketsRepo(),
        is_task=True, resources_repo=resources_repo,
    )
    assert ws.duration_minutes == 30


def test_unrelated_resource_rejected_even_for_task(svc):
    creator_user_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=uuid.uuid4(), created_by=creator_user_id)
    resources_repo = FakeResourcesRepo({creator_user_id: uuid.uuid4()})

    with pytest.raises(WorkSessionAuthorizationError) as exc:
        svc.create(
            resource_id=uuid.uuid4(), ticket=ticket, work_date=date.today(),
            duration_minutes=30, created_by=creator_user_id,
            work_sessions_repo=FakeWorkSessionsRepo(), tickets_repo=FakeTicketsRepo(),
            is_task=True, resources_repo=resources_repo,
        )
    assert exc.value.code == "not_assigned"


def test_creator_check_ignored_for_regular_ticket(svc):
    """Sin `is_task=True` (Ticket normal), el creador NO se agrega automáticamente a la
    ownership — sin regresión sobre la regla ya vigente para Ticket."""
    creator_user_id = uuid.uuid4()
    creator_resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=uuid.uuid4(), created_by=creator_user_id)
    resources_repo = FakeResourcesRepo({creator_user_id: creator_resource_id})

    with pytest.raises(WorkSessionAuthorizationError):
        svc.create(
            resource_id=creator_resource_id, ticket=ticket, work_date=date.today(),
            duration_minutes=30, created_by=creator_user_id,
            work_sessions_repo=FakeWorkSessionsRepo(), tickets_repo=FakeTicketsRepo(),
            is_task=False, resources_repo=resources_repo,
        )
