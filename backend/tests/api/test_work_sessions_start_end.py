"""US1 (Fase 2.1) — hora de inicio/fin en el registro de tiempo (Escenario 1 del quickstart)."""
from datetime import date


def _assign(client, ticket_id, resource_id):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": "resolver"})


def test_create_with_start_end_calculates_duration(client, make_ticket, ticket_resource,
                                                    resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    today = date.today().isoformat()
    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": today,
        "started_at": f"{today}T14:00:00-05:00", "ended_at": f"{today}T18:00:00-05:00",
        "note": "con horas",
    }, headers=resolver_auth)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["duration_minutes"] == 240
    assert data["started_at"] is not None
    assert data["ended_at"] is not None


def test_create_ignores_explicit_duration_when_range_present(client, make_ticket,
                                                              ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    today = date.today().isoformat()
    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": today, "duration_minutes": 999,
        "started_at": f"{today}T09:00:00-05:00", "ended_at": f"{today}T09:30:00-05:00",
    }, headers=resolver_auth)
    assert response.status_code == 201, response.get_json()
    assert response.get_json()["duration_minutes"] == 30


def test_create_without_range_still_requires_duration(client, make_ticket, ticket_resource,
                                                       resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": date.today().isoformat(),
    }, headers=resolver_auth)
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_duration"


def test_create_rejects_incomplete_range(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    today = date.today().isoformat()
    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": today, "started_at": f"{today}T09:00:00-05:00",
    }, headers=resolver_auth)
    assert response.status_code == 400
    assert response.get_json()["error"] == "incomplete_time_range"


def test_create_rejects_end_before_start(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    today = date.today().isoformat()
    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": today,
        "started_at": f"{today}T18:00:00-05:00", "ended_at": f"{today}T09:00:00-05:00",
    }, headers=resolver_auth)
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_time_range"


def test_manual_duration_without_range_still_works(client, make_ticket, ticket_resource,
                                                    resolver_auth):
    """Compatibilidad con Fase 2 original: sin horas, solo duración manual."""
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": date.today().isoformat(),
        "duration_minutes": 90,
    }, headers=resolver_auth)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["duration_minutes"] == 90
    assert data["started_at"] is None
    assert data["ended_at"] is None
