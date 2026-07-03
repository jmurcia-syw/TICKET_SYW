"""US4 — Panel de Asignación (Escenario 5 del quickstart)."""


def test_panel_counts_by_resource_and_status(client, make_ticket, ticket_resource):
    t1 = make_ticket()
    t2 = make_ticket()
    client.post(f"/api/tickets/{t1['id']}/assign",
                json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    client.post(f"/api/tickets/{t2['id']}/assign",
                json={"assignee_id": ticket_resource["id"], "mode": "resolver"})

    response = client.get("/api/assignment-panel")
    assert response.status_code == 200
    data = response.get_json()
    row = next(r for r in data["matrix"] if r["resource"]["id"] == ticket_resource["id"])
    assert row["counts"].get("contacto", 0) >= 2
    assert row["total"] >= 2


def test_panel_lists_unassigned_new_oldest_first(client, make_ticket):
    # el panel prioriza los NUEVOS más antiguos (cap 100); el ticket recién creado
    # puede no entrar al tope si hay backlog — se valida orden y consistencia
    ticket = make_ticket()
    data = client.get("/api/assignment-panel").get_json()
    unassigned = data["unassigned_new"]
    assert len(unassigned) >= 1
    created = [t["created_at"] for t in unassigned]
    assert created == sorted(created)  # más antiguos primero
    # el ticket nuevo sí es visible en el listado general filtrado por NUEVO
    listing = client.get(f"/api/tickets?status=nuevo&search={ticket['ticket_number']}").get_json()
    assert any(t["id"] == ticket["id"] for t in listing["items"])


def test_panel_status_filter(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/assign",
                json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    data = client.get("/api/assignment-panel?statuses=en_analisis").get_json()
    row = next((r for r in data["matrix"] if r["resource"]["id"] == ticket_resource["id"]), None)
    # el ticket está en contacto: con filtro en_analisis no debe contar
    assert row is None or "contacto" not in row["counts"]


def test_panel_requires_permission(anon_client, resolver_token):
    response = anon_client.get("/api/assignment-panel",
                               headers={"Authorization": f"Bearer {resolver_token}"})
    assert response.status_code == 403


def test_panel_invalid_status_rejected(client):
    response = client.get("/api/assignment-panel?statuses=volando")
    assert response.status_code == 400
