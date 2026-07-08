"""US3 — Consultar tiempos registrados por recurso y período (Escenario 3 del quickstart)."""
from datetime import date, timedelta


def _assign(client, ticket_id, resource_id):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": "resolver"})


def _create_ws(client, ticket_id, auth, duration_minutes, work_date):
    return client.post("/api/work-sessions", json={
        "ticket_id": ticket_id, "work_date": work_date.isoformat(),
        "duration_minutes": duration_minutes,
    }, headers=auth)


def test_summary_totals_match_manual_sum_and_flags_days_without_entries(
        client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    today = date.today()
    yesterday = today - timedelta(days=1)
    _create_ws(client, ticket["id"], resolver_auth, 60, yesterday)
    _create_ws(client, ticket["id"], resolver_auth, 30, yesterday)
    # sin registro hoy

    response = client.get("/api/work-sessions/summary", query_string={
        "resource_id": ticket_resource["id"],
        "date_from": yesterday.isoformat(), "date_to": today.isoformat(),
    })  # client por defecto = Admin (work_sessions:view_all)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    days_by_date = {d["work_date"]: d for d in data["days"]}
    assert days_by_date[yesterday.isoformat()]["total_minutes"] == 90
    assert days_by_date[yesterday.isoformat()]["sin_registro"] is False
    assert days_by_date[today.isoformat()]["total_minutes"] == 0
    assert days_by_date[today.isoformat()]["sin_registro"] is True
    assert data["total_minutes"] == 90


def test_resource_without_view_all_cannot_query_another_resource(
        client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    today = date.today()
    _create_ws(client, ticket["id"], resolver_auth, 60, today)

    other_resource_id = "00000000-0000-0000-0000-000000000000"
    response = client.get("/api/work-sessions/summary", query_string={
        "resource_id": other_resource_id,
        "date_from": today.isoformat(), "date_to": today.isoformat(),
    }, headers=resolver_auth)
    assert response.status_code == 200
    data = response.get_json()
    # se ignora el resource_id ajeno y se fuerza al propio
    assert data["resource_id"] == ticket_resource["id"]
    assert data["total_minutes"] == 60


def test_summary_rejects_range_over_92_days(client, ticket_resource):
    today = date.today()
    response = client.get("/api/work-sessions/summary", query_string={
        "resource_id": ticket_resource["id"],
        "date_from": (today - timedelta(days=200)).isoformat(), "date_to": today.isoformat(),
    })
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"
