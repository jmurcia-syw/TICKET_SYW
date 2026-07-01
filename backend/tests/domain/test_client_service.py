import uuid

import pytest

from backend.domain.services.client_service import ClientService, ClientBusinessError


class FakeClient:
    def __init__(self, id_, name):
        self.id = id_
        self.name = name


class FakeClientRepo:
    def __init__(self, existing=None):
        self._existing = existing

    def get_by_name(self, name):
        return self._existing


class FakeProjectsRepo:
    def __init__(self, active_count=0):
        self._active_count = active_count

    def list_paginated(self, client_id, active=None):
        return ([object()] * self._active_count, self._active_count)


def test_validate_unique_name_passes_when_no_existing_client():
    svc = ClientService()
    svc.validate_unique_name("Acme", repo=FakeClientRepo(existing=None))


def test_validate_unique_name_raises_409_on_duplicate():
    other = FakeClient(uuid.uuid4(), "Acme")
    svc = ClientService()
    with pytest.raises(ClientBusinessError) as exc_info:
        svc.validate_unique_name("Acme", repo=FakeClientRepo(existing=other))
    err = exc_info.value
    assert err.code == "name_duplicate"
    assert err.status_code == 409


def test_validate_unique_name_allows_renaming_self():
    self_id = uuid.uuid4()
    same_record = FakeClient(self_id, "Acme")
    svc = ClientService()
    # Editing the same client back to its own name must not raise
    svc.validate_unique_name("Acme", existing_id=self_id, repo=FakeClientRepo(existing=same_record))


def test_get_deactivation_impact_reports_active_projects():
    svc = ClientService()
    impact = svc.get_deactivation_impact(uuid.uuid4(), projects_repo=FakeProjectsRepo(active_count=3))
    assert impact == {"active_projects_count": 3, "open_tickets_count": 0}
