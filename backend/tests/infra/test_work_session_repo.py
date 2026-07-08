"""Tests de repositorio: work_sessions + historial de ediciones (work_session_edits)."""
from datetime import date, timedelta

import pytest

from backend.domain.entities.work_session import WorkSession
from backend.infra.repositories.work_session_repo import WorkSessionRepository


@pytest.fixture()
def repo(db_session):
    return WorkSessionRepository(db_session)


def _make_ws(resource_id, ticket_id, created_by, work_date=None, minutes=60, note=None):
    return WorkSession.create(
        resource_id=resource_id, ticket_id=ticket_id, work_date=work_date or date.today(),
        duration_minutes=minutes, created_by=created_by, note=note,
    )


def test_create_writes_created_edit_row(repo, db_session, ticket_resource, make_ticket, admin_token):
    from backend.infra.repositories.user_repo import UserRepository
    admin = UserRepository(db_session).get_by_email("admin@sywork.net")
    ticket = make_ticket()

    ws = _make_ws(ticket_resource["id"], ticket["id"], admin.id, note="Análisis inicial")
    created = repo.create(ws)

    assert created.id is not None
    fetched = repo.get_by_id(created.id)
    assert fetched.duration_minutes == 60
    assert fetched.note == "Análisis inicial"

    from backend.infra.models.work_session_model import WorkSessionEditModel
    edits = (db_session.query(WorkSessionEditModel)
             .filter(WorkSessionEditModel.work_session_id == created.id).all())
    assert len(edits) == 1
    assert edits[0].action == "created"
    assert edits[0].previous_values is None
    assert edits[0].new_values["duration_minutes"] == 60


def test_update_writes_updated_edit_with_previous_and_new_values(repo, db_session, ticket_resource,
                                                                  make_ticket):
    from backend.infra.repositories.user_repo import UserRepository
    admin = UserRepository(db_session).get_by_email("admin@sywork.net")
    ticket = make_ticket()
    created = repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id, minutes=60))

    updated = repo.update(created.id, admin.id, duration_minutes=90, note="Actualizado")
    assert updated.duration_minutes == 90
    assert updated.note == "Actualizado"
    assert updated.updated_by == admin.id

    from backend.infra.models.work_session_model import WorkSessionEditModel
    edits = (db_session.query(WorkSessionEditModel)
             .filter(WorkSessionEditModel.work_session_id == created.id,
                     WorkSessionEditModel.action == "updated").all())
    assert len(edits) == 1
    assert edits[0].previous_values["duration_minutes"] == 60
    assert edits[0].new_values["duration_minutes"] == 90


def test_soft_delete_excludes_from_get_and_writes_deleted_edit(repo, db_session, ticket_resource,
                                                                make_ticket):
    from backend.infra.repositories.user_repo import UserRepository
    admin = UserRepository(db_session).get_by_email("admin@sywork.net")
    ticket = make_ticket()
    created = repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id))

    assert repo.soft_delete(created.id, admin.id) is True
    assert repo.get_by_id(created.id) is None

    from backend.infra.models.work_session_model import WorkSessionEditModel
    edits = (db_session.query(WorkSessionEditModel)
             .filter(WorkSessionEditModel.work_session_id == created.id,
                     WorkSessionEditModel.action == "deleted").all())
    assert len(edits) == 1
    assert edits[0].previous_values is not None
    assert edits[0].new_values is None


def test_sum_minutes_for_day_aggregates_only_active_entries(repo, db_session, ticket_resource,
                                                              make_ticket):
    from backend.infra.repositories.user_repo import UserRepository
    admin = UserRepository(db_session).get_by_email("admin@sywork.net")
    ticket = make_ticket()
    today = date.today()
    repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id, work_date=today, minutes=90))
    deleted = repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id, work_date=today, minutes=200))
    repo.soft_delete(deleted.id, admin.id)

    assert repo.sum_minutes_for_day(ticket_resource["id"], today) == 90


def test_aggregate_by_resource_and_day_groups_by_date(repo, db_session, ticket_resource, make_ticket):
    from backend.infra.repositories.user_repo import UserRepository
    admin = UserRepository(db_session).get_by_email("admin@sywork.net")
    ticket = make_ticket()
    today = date.today()
    yesterday = today - timedelta(days=1)
    repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id, work_date=today, minutes=60))
    repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id, work_date=today, minutes=30))
    repo.create(_make_ws(ticket_resource["id"], ticket["id"], admin.id, work_date=yesterday, minutes=45))

    rows = repo.aggregate_by_resource_and_day(ticket_resource["id"], yesterday, today)
    by_date = {r["work_date"]: r["total_minutes"] for r in rows}
    assert by_date[today] == 90
    assert by_date[yesterday] == 45
