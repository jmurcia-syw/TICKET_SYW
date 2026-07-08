"""US2 — Corregir o eliminar un registro de tiempo (Escenario 2 del quickstart)."""
from datetime import date, timedelta


def _assign(client, ticket_id, resource_id):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": "resolver"})


def _create_ws(client, ticket_id, auth, duration_minutes=60, work_date=None, note=None):
    payload = {
        "ticket_id": ticket_id, "work_date": (work_date or date.today()).isoformat(),
        "duration_minutes": duration_minutes,
    }
    if note is not None:
        payload["note"] = note
    return client.post("/api/work-sessions", json=payload, headers=auth)


def test_update_recalculates_daily_summary(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    created = _create_ws(client, ticket["id"], resolver_auth, duration_minutes=60).get_json()

    response = client.patch(f"/api/work-sessions/{created['id']}",
                            json={"duration_minutes": 90, "note": "actualizado"}, headers=resolver_auth)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["duration_minutes"] == 90
    assert data["note"] == "actualizado"


def test_update_outside_edit_window_rejected(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    old_date = date.today() - timedelta(days=10)
    created = _create_ws(client, ticket["id"], resolver_auth, duration_minutes=60,
                         work_date=old_date).get_json()

    response = client.patch(f"/api/work-sessions/{created['id']}",
                            json={"duration_minutes": 30}, headers=resolver_auth)
    assert response.status_code == 403
    assert response.get_json()["error"] == "edit_window_expired"


def test_admin_can_edit_outside_window(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    old_date = date.today() - timedelta(days=10)
    created = _create_ws(client, ticket["id"], resolver_auth, duration_minutes=60,
                         work_date=old_date).get_json()

    response = client.patch(f"/api/work-sessions/{created['id']}", json={"duration_minutes": 30})
    assert response.status_code == 200, response.get_json()


def test_delete_writes_deleted_edit_and_removes_from_listing(client, make_ticket, ticket_resource,
                                                              resolver_auth, db_session):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    created = _create_ws(client, ticket["id"], resolver_auth, duration_minutes=45).get_json()

    response = client.delete(f"/api/work-sessions/{created['id']}", headers=resolver_auth)
    assert response.status_code == 204

    listing = client.get("/api/work-sessions", headers=resolver_auth)
    assert not any(item["id"] == created["id"] for item in listing.get_json()["items"])

    from backend.infra.models.work_session_model import WorkSessionEditModel
    import uuid
    edits = (db_session.query(WorkSessionEditModel)
             .filter(WorkSessionEditModel.work_session_id == uuid.UUID(created["id"]),
                     WorkSessionEditModel.action == "deleted").all())
    assert len(edits) == 1
    assert edits[0].previous_values is not None


def test_edit_forbidden_for_non_owner(client, make_ticket, ticket_resource, resolver_auth,
                                      qm_token):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    created = _create_ws(client, ticket["id"], resolver_auth, duration_minutes=45).get_json()

    response = client.patch(f"/api/work-sessions/{created['id']}", json={"duration_minutes": 10},
                            headers={"Authorization": f"Bearer {qm_token}"})
    assert response.status_code == 403
    assert response.get_json()["error"] == "forbidden"
