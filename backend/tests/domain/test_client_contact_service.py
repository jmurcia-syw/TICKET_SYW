import uuid

import pytest

from backend.domain.services.client_contact_service import ClientContactService, ClientContactBusinessError


class FakeClient:
    def __init__(self, active=True):
        self.id = uuid.uuid4()
        self.active = active


class FakeClientsRepo:
    def __init__(self, client=None):
        self._client = client

    def get_by_id(self, client_id):
        return self._client


class FakeUsersRepo:
    def __init__(self, existing=None):
        self._existing = existing

    def get_by_email(self, email):
        return self._existing


def test_validate_create_passes_with_active_client_and_free_email():
    svc = ClientContactService()
    svc.validate_create(
        client_id=uuid.uuid4(), email="new@cliente.com",
        clients_repo=FakeClientsRepo(FakeClient(active=True)), users_repo=FakeUsersRepo(existing=None),
    )


def test_validate_create_raises_404_when_client_not_found():
    svc = ClientContactService()
    with pytest.raises(ClientContactBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), email="new@cliente.com",
            clients_repo=FakeClientsRepo(None), users_repo=FakeUsersRepo(existing=None),
        )
    err = exc_info.value
    assert err.code == "client_not_found"
    assert err.status_code == 404


def test_validate_create_raises_404_when_client_inactive():
    svc = ClientContactService()
    with pytest.raises(ClientContactBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), email="new@cliente.com",
            clients_repo=FakeClientsRepo(FakeClient(active=False)), users_repo=FakeUsersRepo(existing=None),
        )
    assert exc_info.value.code == "client_not_found"
    assert exc_info.value.status_code == 404


def test_validate_create_raises_409_when_email_in_use():
    svc = ClientContactService()
    with pytest.raises(ClientContactBusinessError) as exc_info:
        svc.validate_create(
            client_id=uuid.uuid4(), email="dup@cliente.com",
            clients_repo=FakeClientsRepo(FakeClient(active=True)),
            users_repo=FakeUsersRepo(existing=object()),
        )
    err = exc_info.value
    assert err.code == "email_in_use"
    assert err.status_code == 409
