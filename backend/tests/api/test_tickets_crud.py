"""US1 — Registro y consulta de tickets (Escenario 2 del quickstart)."""


def test_ticket_is_born_in_nuevo_with_number(make_ticket):
    ticket = make_ticket()
    assert ticket["status"] == "nuevo"
    assert ticket["ticket_number"].startswith("TK-")
    assert ticket["valid_actions"] == ["assign_resolver", "assign_qm", "cancel"]


def test_ticket_numbers_are_unique_and_increasing(make_ticket):
    n1 = int(make_ticket()["ticket_number"].split("-")[1])
    n2 = int(make_ticket()["ticket_number"].split("-")[1])
    assert n2 > n1


def test_create_requires_mandatory_fields(client, ticket_client):
    response = client.post("/api/tickets", json={"title": "solo título"})
    assert response.status_code == 400
    assert "requerido" in response.get_json()["message"]


def test_create_rejects_invalid_enum(client, ticket_client):
    response = client.post("/api/tickets", json={
        "title": "x", "description": "y", "ticket_type": "bug",
        "priority": "high", "severity": "s2", "client_id": ticket_client["id"],
    })
    assert response.status_code == 400
    assert "ticket_type" in response.get_json()["message"]


def test_create_rejects_project_of_other_client(client, make_ticket, unique_name):
    other = client.post("/api/clients", json={"name": f"Otro Cliente {unique_name}"}).get_json()
    project = client.post("/api/projects", json={
        "client_id": other["id"], "name": f"Proyecto ajeno {unique_name}",
        "start_date": "2026-01-01",
    }).get_json()
    response = client.post("/api/tickets", json={
        "title": "x", "description": "y", "ticket_type": "incident",
        "priority": "low", "severity": "s4",
        "client_id": make_ticket()["client"]["id"], "project_id": project["id"],
    })
    assert response.status_code == 400
    assert "no pertenece" in response.get_json()["message"]


def test_list_filters_by_status_and_client(client, make_ticket, ticket_client):
    make_ticket()
    response = client.get(f"/api/tickets?status=nuevo&client_id={ticket_client['id']}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] >= 1
    assert all(t["status"] == "nuevo" for t in data["items"])
    assert all(t["client"]["id"] == ticket_client["id"] for t in data["items"])


def test_detail_includes_locked_fields_and_histories(client, make_ticket):
    ticket = make_ticket()
    detail = client.get(f"/api/tickets/{ticket['id']}").get_json()
    assert "status" in detail["locked_fields"]
    assert detail["comments"] == []
    assert detail["transitions"] == []
    assert detail["close_eligible"] is False


def test_patch_cannot_edit_status(client, make_ticket):
    ticket = make_ticket()
    response = client.patch(f"/api/tickets/{ticket['id']}", json={"status": "resuelto"})
    assert response.status_code == 400


def test_patch_editable_field_in_nuevo(client, make_ticket):
    ticket = make_ticket()
    response = client.patch(f"/api/tickets/{ticket['id']}", json={"priority": "critical"})
    assert response.status_code == 200
    assert response.get_json()["priority"] == "critical"
