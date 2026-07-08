"""US1 — Alta de horas trabajadas en un ticket (Escenario 1 del quickstart)."""
from datetime import date, timedelta


def _assign(client, ticket_id, resource_id):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": "resolver"})


def _create_ws(client, ticket_id, duration_minutes=90, work_date=None, note=None, auth=None):
    payload = {
        "ticket_id": ticket_id,
        "work_date": (work_date or date.today()).isoformat(),
        "duration_minutes": duration_minutes,
    }
    if note is not None:
        payload["note"] = note
    return client.post("/api/work-sessions", json=payload, headers=auth)


def test_create_ok_appears_in_list(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    response = _create_ws(client, ticket["id"], duration_minutes=90, note="Análisis inicial",
                          auth=resolver_auth)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["duration_minutes"] == 90
    assert data["ticket_id"] == ticket["id"]

    listing = client.get("/api/work-sessions", headers=resolver_auth)
    assert listing.status_code == 200
    assert any(item["id"] == data["id"] for item in listing.get_json()["items"])


def test_create_rejects_ticket_not_assigned_to_caller(client, make_ticket, resolver_auth,
                                                       ticket_resource):
    # ticket_resource crea el recurso vinculado al resolutor de prueba, pero el ticket
    # no se le asigna — así se aisla la regla de pertenencia (no_resource_profile no aplica).
    ticket = make_ticket()
    response = _create_ws(client, ticket["id"], auth=resolver_auth)
    assert response.status_code == 403
    assert response.get_json()["error"] == "not_assigned"


def test_create_rejects_daily_limit_exceeded(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    first = _create_ws(client, ticket["id"], duration_minutes=1400, auth=resolver_auth)
    assert first.status_code == 201
    second = _create_ws(client, ticket["id"], duration_minutes=100, auth=resolver_auth)
    assert second.status_code == 400
    assert second.get_json()["error"] == "daily_limit_exceeded"


def test_create_rejects_future_date(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    response = _create_ws(client, ticket["id"], work_date=date.today() + timedelta(days=1),
                          auth=resolver_auth)
    assert response.status_code == 400
    assert response.get_json()["error"] == "future_date"


def test_create_rejects_zero_duration(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    response = _create_ws(client, ticket["id"], duration_minutes=0, auth=resolver_auth)
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_duration"


def test_create_rejects_closed_ticket_without_manage_all(client, make_ticket, ticket_resource,
                                                          resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    # Admin (client por defecto) cierra el ticket vía flujo mínimo no es objeto de este test;
    # se fuerza el estado directamente para aislar la regla de negocio bajo prueba.
    from backend.infra.database import get_db
    from backend.infra.repositories.ticket_repo import TicketRepository
    TicketRepository(get_db()).update_fields(ticket["id"], status="cerrado")

    response = _create_ws(client, ticket["id"], auth=resolver_auth)
    assert response.status_code == 409
    assert response.get_json()["error"] == "ticket_closed"


def test_admin_manage_all_bypasses_closed_ticket(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    from backend.infra.database import get_db
    from backend.infra.repositories.ticket_repo import TicketRepository
    TicketRepository(get_db()).update_fields(ticket["id"], status="cerrado")

    response = client.post("/api/work-sessions", json={
        "ticket_id": ticket["id"], "work_date": date.today().isoformat(),
        "duration_minutes": 30, "resource_id": ticket_resource["id"],
    })  # client por defecto = Admin (work_sessions:manage_all)
    assert response.status_code == 201, response.get_json()
