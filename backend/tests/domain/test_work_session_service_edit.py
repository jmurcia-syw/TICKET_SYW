import uuid
from datetime import date, timedelta

import pytest

from backend.domain.entities.work_session import EDIT_WINDOW_DAYS
from backend.domain.services.work_session_service import (
    WorkSessionService, WorkSessionValidationError, WorkSessionAuthorizationError,
)


class FakeWorkSession:
    def __init__(self, work_date, resource_id=None, duration_minutes=60):
        self.id = uuid.uuid4()
        self.resource_id = resource_id or uuid.uuid4()
        self.work_date = work_date
        self.duration_minutes = duration_minutes
        self.started_at = None
        self.ended_at = None


class FakeWorkSessionsRepo:
    def __init__(self, existing_minutes=0):
        self._existing_minutes = existing_minutes
        self.updated = None
        self.deleted_id = None

    def sum_minutes_for_day(self, resource_id, work_date, exclude_id=None):
        return self._existing_minutes

    def update(self, work_session_id, actor_id, duration_minutes=None, note=None,
              started_at=None, ended_at=None):
        self.updated = (work_session_id, actor_id, duration_minutes, note)
        return "updated-result"

    def soft_delete(self, work_session_id, actor_id):
        self.deleted_id = work_session_id
        return True


@pytest.fixture()
def svc():
    return WorkSessionService()


def test_update_within_window_ok(svc):
    existing = FakeWorkSession(work_date=date.today())
    repo = FakeWorkSessionsRepo()
    result = svc.update(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo,
                        duration_minutes=90)
    assert result == "updated-result"
    assert repo.updated[2] == 90


def test_update_outside_window_rejected_without_allow_any(svc):
    old_date = date.today() - timedelta(days=EDIT_WINDOW_DAYS + 1)
    existing = FakeWorkSession(work_date=old_date)
    with pytest.raises(WorkSessionAuthorizationError) as exc:
        svc.update(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo(),
                  duration_minutes=30)
    assert exc.value.code == "edit_window_expired"
    assert exc.value.status_code == 403


def test_update_outside_window_allowed_with_allow_any(svc):
    old_date = date.today() - timedelta(days=EDIT_WINDOW_DAYS + 10)
    existing = FakeWorkSession(work_date=old_date)
    repo = FakeWorkSessionsRepo()
    result = svc.update(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo,
                        duration_minutes=45, allow_any=True)
    assert result == "updated-result"


def test_update_recalculates_daily_limit_with_new_value(svc):
    existing = FakeWorkSession(work_date=date.today(), duration_minutes=60)
    repo = FakeWorkSessionsRepo(existing_minutes=1400)  # ya sin contar el propio (exclude_id)
    with pytest.raises(WorkSessionValidationError) as exc:
        svc.update(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo,
                  duration_minutes=100)
    assert exc.value.code == "daily_limit_exceeded"


def test_delete_within_window_ok(svc):
    existing = FakeWorkSession(work_date=date.today())
    repo = FakeWorkSessionsRepo()
    svc.delete(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo)
    assert repo.deleted_id == existing.id


def test_delete_outside_window_rejected_without_allow_any(svc):
    old_date = date.today() - timedelta(days=EDIT_WINDOW_DAYS + 1)
    existing = FakeWorkSession(work_date=old_date)
    with pytest.raises(WorkSessionAuthorizationError):
        svc.delete(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=FakeWorkSessionsRepo())


def test_delete_outside_window_allowed_for_admin(svc):
    old_date = date.today() - timedelta(days=EDIT_WINDOW_DAYS + 30)
    existing = FakeWorkSession(work_date=old_date)
    repo = FakeWorkSessionsRepo()
    svc.delete(existing=existing, actor_id=uuid.uuid4(), work_sessions_repo=repo, allow_any=True)
    assert repo.deleted_id == existing.id
