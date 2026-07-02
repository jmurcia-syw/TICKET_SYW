import uuid
from datetime import date

import pytest

from backend.domain.services.project_service import ProjectService, ProjectBusinessError


class FakeClient:
    def __init__(self, active=True):
        self.active = active


class FakeClientsRepo:
    def __init__(self, client=None):
        self._client = client

    def get_by_id(self, client_id):
        return self._client


class FakeProjectsRepo:
    def __init__(self, existing=None):
        self._existing = existing

    def get_by_client_and_name(self, client_id, name):
        return self._existing


def test_validate_create_raises_404_when_client_missing():
    """Regression: client_not_found must map to 404, not the blanket 409 it had before."""
    svc = ProjectService()
    with pytest.raises(ProjectBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), name="Proj", start_date=date(2026, 1, 1), end_date=None,
            clients_repo=FakeClientsRepo(client=None),
        )
    err = exc_info.value
    assert err.code == "client_not_found"
    assert err.status_code == 404


def test_validate_create_raises_409_when_client_inactive():
    svc = ProjectService()
    with pytest.raises(ProjectBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), name="Proj", start_date=date(2026, 1, 1), end_date=None,
            clients_repo=FakeClientsRepo(client=FakeClient(active=False)),
        )
    err = exc_info.value
    assert err.code == "client_inactive"
    assert err.status_code == 409


def test_validate_create_raises_400_when_end_before_start():
    """Regression: invalid_dates is a validation error (400), not a conflict (409)."""
    svc = ProjectService()
    with pytest.raises(ProjectBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), name="Proj",
            start_date=date(2026, 6, 1), end_date=date(2026, 1, 1),
            clients_repo=FakeClientsRepo(client=FakeClient(active=True)),
        )
    err = exc_info.value
    assert err.code == "invalid_dates"
    assert err.status_code == 400


def test_validate_create_raises_409_on_duplicate_name_for_client():
    svc = ProjectService()
    with pytest.raises(ProjectBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), name="Proj", start_date=date(2026, 1, 1), end_date=None,
            clients_repo=FakeClientsRepo(client=FakeClient(active=True)),
            projects_repo=FakeProjectsRepo(existing=object()),
        )
    err = exc_info.value
    assert err.code == "name_duplicate"
    assert err.status_code == 409


def test_validate_create_passes_for_valid_input():
    svc = ProjectService()
    svc.validate_create(
        client_id=uuid.uuid4(), name="Proj", start_date=date(2026, 1, 1), end_date=date(2026, 6, 1),
        clients_repo=FakeClientsRepo(client=FakeClient(active=True)),
        projects_repo=FakeProjectsRepo(existing=None),
    )
