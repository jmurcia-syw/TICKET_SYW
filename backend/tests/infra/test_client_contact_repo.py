"""Tests de repositorio: client_contacts (perfil del rol Encargado)."""
import uuid

import pytest

from backend.domain.entities.client_contact import ClientContact
from backend.domain.entities.user import User
from backend.infra.repositories.client_contact_repo import ClientContactRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.repositories.user_repo import UserRepository


@pytest.fixture()
def repo(db_session):
    return ClientContactRepository(db_session)


def _make_encargado_user(db_session, unique_name):
    role = RoleRepository(db_session).get_by_name("Encargado")
    user = User(
        id=uuid.uuid4(), email=f"encargado.{unique_name}@clienteexterno.com",
        username=f"encargado_{unique_name}", role=role,
    )
    return UserRepository(db_session).create(user)


def test_create_and_get_by_user_id(repo, db_session, unique_name, ticket_client):
    user = _make_encargado_user(db_session, unique_name)
    contact = ClientContact(id=uuid.uuid4(), user_id=user.id, client_id=uuid.UUID(ticket_client["id"]))
    created = repo.create(contact)

    assert created.id is not None
    fetched = repo.get_by_user_id(user.id)
    assert fetched is not None
    assert fetched.client_id == uuid.UUID(ticket_client["id"])


def test_get_by_user_id_returns_none_when_not_found(repo):
    assert repo.get_by_user_id(uuid.uuid4()) is None


def test_list_paginated_filters_by_client_id(repo, db_session, unique_name, ticket_client):
    user1 = _make_encargado_user(db_session, unique_name + "a")
    user2 = _make_encargado_user(db_session, unique_name + "b")
    repo.create(ClientContact(id=uuid.uuid4(), user_id=user1.id, client_id=uuid.UUID(ticket_client["id"])))
    repo.create(ClientContact(id=uuid.uuid4(), user_id=user2.id, client_id=uuid.UUID(ticket_client["id"])))

    items, total = repo.list_paginated(client_id=uuid.UUID(ticket_client["id"]))
    assert total >= 2
    assert all(i.client_id == uuid.UUID(ticket_client["id"]) for i in items)
