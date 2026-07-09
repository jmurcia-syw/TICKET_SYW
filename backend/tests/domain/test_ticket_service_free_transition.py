"""spec 009, US2 — transición libre de estado de Tarea/Subtarea (FR-003/FR-004/FR-005):
cualquier estado del catálogo compartido con Ticket, sin restricción de secuencia, con
comentario obligatorio. Reemplaza task_fsm.py (spec 008)."""
import uuid

import pytest

from backend.domain.entities.ticket import Ticket, STATUSES
from backend.domain.services.ticket_service import TicketService, TicketValidationError


class FakeTicketsRepo:
    def __init__(self, ticket: Ticket):
        self._ticket = ticket
        self.transitions: list[tuple] = []

    def update_fields(self, ticket_id, **fields):
        for k, v in fields.items():
            setattr(self._ticket, k, v)
        return self._ticket

    def add_transition(self, ticket_id, from_status, to_status, actor_id, comment_id=None, commit=True):
        self.transitions.append((from_status, to_status, actor_id, comment_id))

    def get_by_id(self, ticket_id):
        return self._ticket


class FakeCommentsRepo:
    def __init__(self):
        self.added = []

    def add(self, comment, commit=True):
        self.added.append(comment)
        return comment


def _make_task(status="nuevo"):
    return Ticket(
        id=uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="medium", severity="s3",
        client_id=uuid.uuid4(), created_by=uuid.uuid4(), status=status,
    )


@pytest.mark.parametrize("from_status,to_status", [
    ("nuevo", "cerrado"),
    ("cerrado", "nuevo"),
    ("resuelto", "en_analisis"),
    ("cancelado", "cancelado"),
])
def test_free_transition_allows_any_to_any(from_status, to_status):
    ticket = _make_task(status=from_status)
    tickets_repo = FakeTicketsRepo(ticket)
    comments_repo = FakeCommentsRepo()
    svc = TicketService()

    updated = svc.free_transition_task(
        ticket, to_status, "Motivo del cambio", uuid.uuid4(),
        tickets_repo=tickets_repo, comments_repo=comments_repo,
    )
    assert updated.status == to_status
    assert len(tickets_repo.transitions) == 1
    assert tickets_repo.transitions[0][:2] == (from_status, to_status)
    assert len(comments_repo.added) == 1
    assert comments_repo.added[0].comment_type == "comentario_interno"


def test_free_transition_rejects_empty_comment():
    ticket = _make_task()
    svc = TicketService()
    with pytest.raises(TicketValidationError) as exc:
        svc.free_transition_task(
            ticket, "cerrado", "   ", uuid.uuid4(),
            tickets_repo=FakeTicketsRepo(ticket), comments_repo=FakeCommentsRepo(),
        )
    assert exc.value.code == "validation_error"
    assert exc.value.status_code == 400


def test_free_transition_rejects_unknown_status():
    ticket = _make_task()
    svc = TicketService()
    with pytest.raises(TicketValidationError) as exc:
        svc.free_transition_task(
            ticket, "no_existe", "Comentario", uuid.uuid4(),
            tickets_repo=FakeTicketsRepo(ticket), comments_repo=FakeCommentsRepo(),
        )
    assert exc.value.code == "validation_error"


def test_all_statuses_are_reachable_from_each_other():
    """SC-002: ningún estado queda excluido de la transición libre."""
    for status in STATUSES:
        ticket = _make_task(status=status)
        svc = TicketService()
        for target in STATUSES:
            updated = svc.free_transition_task(
                ticket, target, "ok", uuid.uuid4(),
                tickets_repo=FakeTicketsRepo(ticket), comments_repo=FakeCommentsRepo(),
            )
            assert updated.status == target
