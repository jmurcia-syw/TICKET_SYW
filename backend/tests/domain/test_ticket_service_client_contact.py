import uuid

import pytest

from backend.domain.entities.ticket import Ticket
from backend.domain.services.ticket_service import TicketBusinessError, TicketService, TicketValidationError


class FakeClient:
    def __init__(self, active=True):
        self.id = uuid.uuid4()
        self.active = active


class FakeClientsRepo:
    def __init__(self, client=None):
        self._client = client

    def get_by_id(self, client_id):
        return self._client


class FakeContact:
    def __init__(self, client_id):
        self.id = uuid.uuid4()
        self.client_id = client_id


class FakeClientContactsRepo:
    def __init__(self, contact=None):
        self._contact = contact

    def get_by_id(self, contact_id):
        return self._contact


class FakeRole:
    def __init__(self, name):
        self.name = name


class FakeUser:
    def __init__(self, role_name):
        self.role = FakeRole(role_name)


class FakeUsersRepo:
    def __init__(self, user=None):
        self._user = user

    def get_by_id(self, user_id):
        return self._user


def _make_ticket(client_id, created_by=None, status="nuevo"):
    return Ticket(
        id=uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="medium", severity="s3",
        client_id=client_id, created_by=created_by or uuid.uuid4(), status=status,
    )


# ── validate_create (T008/US1) ──────────────────────────────────────────────

def test_validate_create_accepts_client_contact_of_same_client():
    client = FakeClient(active=True)
    contact = FakeContact(client_id=client.id)
    svc = TicketService()
    svc.validate_create(
        client_id=client.id, project_id=None, tool_id=None, process_id=None,
        related_ticket_id=None, clients_repo=FakeClientsRepo(client), projects_repo=None,
        tools_repo=None, processes_repo=None, tickets_repo=None,
        client_contact_id=contact.id, client_contacts_repo=FakeClientContactsRepo(contact),
    )


def test_validate_create_rejects_client_contact_of_other_client():
    client = FakeClient(active=True)
    other_client_id = uuid.uuid4()
    contact = FakeContact(client_id=other_client_id)
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.validate_create(
            client_id=client.id, project_id=None, tool_id=None, process_id=None,
            related_ticket_id=None, clients_repo=FakeClientsRepo(client), projects_repo=None,
            tools_repo=None, processes_repo=None, tickets_repo=None,
            client_contact_id=contact.id, client_contacts_repo=FakeClientContactsRepo(contact),
        )
    assert exc_info.value.code == "client_contact_mismatch"
    assert exc_info.value.status_code == 409


def test_validate_create_rejects_nonexistent_client_contact():
    client = FakeClient(active=True)
    svc = TicketService()
    with pytest.raises(TicketValidationError) as exc_info:
        svc.validate_create(
            client_id=client.id, project_id=None, tool_id=None, process_id=None,
            related_ticket_id=None, clients_repo=FakeClientsRepo(client), projects_repo=None,
            tools_repo=None, processes_repo=None, tickets_repo=None,
            client_contact_id=uuid.uuid4(), client_contacts_repo=FakeClientContactsRepo(None),
        )
    assert exc_info.value.code == "not_found"
    assert exc_info.value.status_code == 404


def test_validate_create_accepts_no_client_contact():
    client = FakeClient(active=True)
    svc = TicketService()
    svc.validate_create(
        client_id=client.id, project_id=None, tool_id=None, process_id=None,
        related_ticket_id=None, clients_repo=FakeClientsRepo(client), projects_repo=None,
        tools_repo=None, processes_repo=None, tickets_repo=None,
    )


# ── validate_patch (T015/US2) ───────────────────────────────────────────────

def test_validate_patch_accepts_reassigning_to_another_contact_of_same_client():
    client_id = uuid.uuid4()
    contact = FakeContact(client_id=client_id)
    ticket = _make_ticket(client_id)
    svc = TicketService()
    clean = svc.validate_patch(
        ticket, {"client_contact_id": str(contact.id)},
        client_contacts_repo=FakeClientContactsRepo(contact),
        users_repo=FakeUsersRepo(FakeUser("Coordinador")),
    )
    assert clean["client_contact_id"] == contact.id


def test_validate_patch_rejects_contact_of_other_client():
    client_id = uuid.uuid4()
    contact = FakeContact(client_id=uuid.uuid4())
    ticket = _make_ticket(client_id)
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.validate_patch(
            ticket, {"client_contact_id": str(contact.id)},
            client_contacts_repo=FakeClientContactsRepo(contact),
            users_repo=FakeUsersRepo(FakeUser("Coordinador")),
        )
    assert exc_info.value.code == "client_contact_mismatch"


def test_validate_patch_rejects_when_creator_is_encargado():
    client_id = uuid.uuid4()
    contact = FakeContact(client_id=client_id)
    ticket = _make_ticket(client_id)
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.validate_patch(
            ticket, {"client_contact_id": str(contact.id)},
            client_contacts_repo=FakeClientContactsRepo(contact),
            users_repo=FakeUsersRepo(FakeUser("Encargado")),
        )
    assert exc_info.value.code == "requester_immutable"


def test_validate_patch_respects_field_locks_when_closed():
    client_id = uuid.uuid4()
    ticket = _make_ticket(client_id, status="cerrado")
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.validate_patch(
            ticket, {"client_contact_id": str(uuid.uuid4())},
            client_contacts_repo=FakeClientContactsRepo(None),
            users_repo=FakeUsersRepo(FakeUser("Coordinador")),
        )
    assert exc_info.value.code == "field_locked"


def test_validate_patch_allows_clearing_client_contact():
    client_id = uuid.uuid4()
    ticket = _make_ticket(client_id)
    svc = TicketService()
    clean = svc.validate_patch(
        ticket, {"client_contact_id": None},
        client_contacts_repo=FakeClientContactsRepo(None),
        users_repo=FakeUsersRepo(FakeUser("Coordinador")),
    )
    assert clean["client_contact_id"] is None
