import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from backend.domain.services.work_session_service import (
    WorkSessionService, WorkSessionValidationError,
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
        self.updated_kwargs = None

    def sum_minutes_for_day(self, resource_id, work_date, exclude_id=None):
        return self._existing_minutes

    def create(self, work_session):
        self.created = work_session
        return work_session

    def update(self, work_session_id, actor_id, **kwargs):
        self.updated_kwargs = kwargs
        return "updated-result"


@pytest.fixture()
def svc():
    return WorkSessionService()


def _dt(hour, minute=0):
    return datetime(2026, 7, 8, hour, minute, tzinfo=timezone.utc)


def test_create_calculates_duration_from_start_end(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    ws = svc.create(
        resource_id=resource_id, ticket=ticket, work_date=date(2026, 7, 8),
        created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
        tickets_repo=FakeTicketsRepo(), started_at=_dt(14), ended_at=_dt(18),
    )
    assert ws.duration_minutes == 240
    assert ws.started_at == _dt(14)
    assert ws.ended_at == _dt(18)


def test_create_ignores_explicit_duration_when_range_given(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    ws = svc.create(
        resource_id=resource_id, ticket=ticket, work_date=date(2026, 7, 8),
        duration_minutes=999, created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
        tickets_repo=FakeTicketsRepo(), started_at=_dt(14), ended_at=_dt(18, 30),
    )
    assert ws.duration_minutes == 270


def test_create_allows_manual_duration_without_range(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    ws = svc.create(
        resource_id=resource_id, ticket=ticket, work_date=date(2026, 7, 8),
        duration_minutes=90, created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
        tickets_repo=FakeTicketsRepo(),
    )
    assert ws.duration_minutes == 90
    assert ws.started_at is None


def test_create_rejects_only_one_end_of_range(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date(2026, 7, 8),
            created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(), started_at=_dt(14),
        )
    assert exc.value.code == "incomplete_time_range"


def test_create_rejects_end_before_start(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date(2026, 7, 8),
            created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(), started_at=_dt(18), ended_at=_dt(14),
        )
    assert exc.value.code == "invalid_time_range"


def test_create_rejects_neither_duration_nor_range(svc):
    resource_id = uuid.uuid4()
    ticket = FakeTicket(assignee_id=resource_id)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.create(
            resource_id=resource_id, ticket=ticket, work_date=date(2026, 7, 8),
            created_by=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
            tickets_repo=FakeTicketsRepo(),
        )
    assert exc.value.code == "invalid_duration"


def test_update_recalculates_duration_when_range_changes(svc):
    from backend.domain.entities.work_session import WorkSession
    existing = WorkSession.create(
        resource_id=uuid.uuid4(), ticket_id=uuid.uuid4(), work_date=date.today(),
        duration_minutes=60, created_by=uuid.uuid4(),
    )
    repo = FakeWorkSessionsRepo()
    svc.update(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo,
              started_at=_dt(9), ended_at=_dt(12))
    assert repo.updated_kwargs["duration_minutes"] == 180


def test_update_keeps_duration_only_when_no_range_given(svc):
    from backend.domain.entities.work_session import WorkSession
    existing = WorkSession.create(
        resource_id=uuid.uuid4(), ticket_id=uuid.uuid4(), work_date=date.today(),
        duration_minutes=60, created_by=uuid.uuid4(),
    )
    repo = FakeWorkSessionsRepo()
    svc.update(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo,
              duration_minutes=90)
    assert repo.updated_kwargs["duration_minutes"] == 90
    assert repo.updated_kwargs["started_at"] is None
    assert repo.updated_kwargs["ended_at"] is None
