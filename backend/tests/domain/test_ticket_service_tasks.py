import uuid

import pytest

from backend.domain.entities.ticket import Ticket
from backend.domain.services.ticket_service import TicketBusinessError, TicketService, TicketValidationError


class FakeRecordTypesRepo:
    def __init__(self, items: dict[str, dict] | None = None, by_name: dict[str, dict] | None = None):
        self._items = items or {}
        self._by_name = by_name or {}

    def get_by_id(self, record_type_id):
        return self._items.get(str(record_type_id))

    def get_by_name(self, name):
        return self._by_name.get(name)


def _catalog_item(name: str, active: bool = True) -> dict:
    return {"id": str(uuid.uuid4()), "name": name, "active": active}


class FakeClient:
    def __init__(self, client_id=None, active=True):
        self.id = client_id or uuid.uuid4()
        self.active = active


class FakeClientsRepo:
    def __init__(self, client=None):
        self._client = client

    def get_by_id(self, client_id):
        return self._client


class FakeTicketsRepo:
    def __init__(self, ticket=None):
        self._ticket = ticket

    def get_by_id(self, ticket_id):
        return self._ticket


def _make_ticket(client_id, ticket_id=None, status="nuevo"):
    return Ticket(
        id=ticket_id or uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="medium", severity="s3",
        client_id=client_id, created_by=uuid.uuid4(), status=status,
    )


# ── resolve_record_type — Fase 3: "Tarea" ya no se rechaza ─────────────────

def test_resolve_record_type_default_still_returns_ticket():
    ticket_item = _catalog_item("Ticket")
    repo = FakeRecordTypesRepo(by_name={"Ticket": ticket_item})
    svc = TicketService()
    resolved = svc.resolve_record_type(None, repo)
    assert str(resolved) == ticket_item["id"]


def test_resolve_record_type_accepts_tarea():
    tarea_item = _catalog_item("Tarea")
    repo = FakeRecordTypesRepo(items={tarea_item["id"]: tarea_item})
    svc = TicketService()
    resolved = svc.resolve_record_type(uuid.UUID(tarea_item["id"]), repo)
    assert str(resolved) == tarea_item["id"]


def test_resolve_record_type_rejects_nonexistent():
    repo = FakeRecordTypesRepo()
    svc = TicketService()
    with pytest.raises(TicketValidationError) as exc_info:
        svc.resolve_record_type(uuid.uuid4(), repo)
    assert exc_info.value.code == "not_found"
    assert exc_info.value.status_code == 404


def test_resolve_record_type_rejects_inactive():
    inactive_item = _catalog_item("Tarea", active=False)
    repo = FakeRecordTypesRepo(items={inactive_item["id"]: inactive_item})
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.resolve_record_type(uuid.UUID(inactive_item["id"]), repo)
    assert exc_info.value.code == "catalog_inactive"


# ── is_task_record_type ──────────────────────────────────────────────────

def test_is_task_record_type_true_for_tarea():
    tarea_item = _catalog_item("Tarea")
    repo = FakeRecordTypesRepo(items={tarea_item["id"]: tarea_item})
    svc = TicketService()
    assert svc.is_task_record_type(uuid.UUID(tarea_item["id"]), repo) is True


def test_is_task_record_type_false_for_ticket():
    ticket_item = _catalog_item("Ticket")
    repo = FakeRecordTypesRepo(items={ticket_item["id"]: ticket_item})
    svc = TicketService()
    assert svc.is_task_record_type(uuid.UUID(ticket_item["id"]), repo) is False


# ── Registro relacionado — mismo Cliente (T020/US2, FR-005) ────────────────

def test_validate_create_accepts_related_ticket_of_same_client():
    client = FakeClient()
    related = _make_ticket(client_id=client.id)
    svc = TicketService()
    svc.validate_create(
        client_id=client.id, project_id=None, tool_id=None, process_id=None,
        related_ticket_id=related.id, clients_repo=FakeClientsRepo(client), projects_repo=None,
        tools_repo=None, processes_repo=None, tickets_repo=FakeTicketsRepo(related),
    )


def test_validate_create_rejects_related_ticket_of_other_client():
    client = FakeClient()
    related = _make_ticket(client_id=uuid.uuid4())
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.validate_create(
            client_id=client.id, project_id=None, tool_id=None, process_id=None,
            related_ticket_id=related.id, clients_repo=FakeClientsRepo(client), projects_repo=None,
            tools_repo=None, processes_repo=None, tickets_repo=FakeTicketsRepo(related),
        )
    assert exc_info.value.code == "related_ticket_mismatch"
    assert exc_info.value.status_code == 409


def test_validate_create_rejects_nonexistent_related_ticket():
    client = FakeClient()
    svc = TicketService()
    with pytest.raises(TicketValidationError) as exc_info:
        svc.validate_create(
            client_id=client.id, project_id=None, tool_id=None, process_id=None,
            related_ticket_id=uuid.uuid4(), clients_repo=FakeClientsRepo(client), projects_repo=None,
            tools_repo=None, processes_repo=None, tickets_repo=FakeTicketsRepo(None),
        )
    assert exc_info.value.code == "not_found"


def test_validate_patch_accepts_related_ticket_of_same_client():
    client_id = uuid.uuid4()
    ticket = _make_ticket(client_id)
    related = _make_ticket(client_id)
    svc = TicketService()
    clean = svc.validate_patch(
        ticket, {"related_ticket_id": str(related.id)}, tickets_repo=FakeTicketsRepo(related),
    )
    assert clean["related_ticket_id"] == related.id


def test_validate_patch_rejects_related_ticket_of_other_client():
    ticket = _make_ticket(uuid.uuid4())
    related = _make_ticket(uuid.uuid4())  # cliente distinto
    svc = TicketService()
    with pytest.raises(TicketBusinessError) as exc_info:
        svc.validate_patch(
            ticket, {"related_ticket_id": str(related.id)}, tickets_repo=FakeTicketsRepo(related),
        )
    assert exc_info.value.code == "related_ticket_mismatch"


def test_validate_patch_rejects_self_reference():
    ticket = _make_ticket(uuid.uuid4())
    svc = TicketService()
    with pytest.raises(TicketValidationError):
        svc.validate_patch(ticket, {"related_ticket_id": str(ticket.id)}, tickets_repo=FakeTicketsRepo(ticket))
