"""Catálogo dinámico de tipo de registro (FR-029/FR-030, Escenario 7 del quickstart)."""


def _record_type_by_name(client, name: str) -> dict:
    items = client.get("/api/catalogs/record-types?active=all").get_json()["items"]
    return next(item for item in items if item["name"] == name)


def test_record_types_seeded_ticket_and_tarea(client):
    response = client.get("/api/catalogs/record-types")
    assert response.status_code == 200
    names = {item["name"] for item in response.get_json()["items"]}
    assert {"Ticket", "Tarea"} <= names


def test_create_ticket_defaults_to_ticket_record_type(make_ticket, client):
    ticket = make_ticket()
    ticket_record_type = _record_type_by_name(client, "Ticket")
    assert ticket["record_type_id"] == ticket_record_type["id"]


def test_create_ticket_with_explicit_ticket_record_type_id(client, make_ticket):
    ticket_record_type = _record_type_by_name(client, "Ticket")
    ticket = make_ticket(record_type_id=ticket_record_type["id"])
    assert ticket["record_type_id"] == ticket_record_type["id"]


def test_create_ticket_with_tarea_record_type_is_allowed(client, ticket_client):
    """Fase 1 rechazaba 'Tarea' (FR-030); Fase 3 (spec 008) la habilitó como record_type_id
    creable — ver backend/tests/api/test_tickets_tasks.py para la cobertura completa."""
    tarea_record_type = _record_type_by_name(client, "Tarea")
    response = client.post("/api/tickets", json={
        "title": "x", "description": "y", "client_id": ticket_client["id"],
        "record_type_id": tarea_record_type["id"],
    })
    assert response.status_code == 201, response.get_json()
    assert response.get_json()["record_type_id"] == tarea_record_type["id"]


def test_deactivate_ticket_record_type_blocked_while_in_use(client, make_ticket):
    make_ticket()
    ticket_record_type = _record_type_by_name(client, "Ticket")
    response = client.patch(f"/api/catalogs/record-types/{ticket_record_type['id']}/deactivate")
    assert response.status_code == 409
    assert response.get_json()["error"] == "in_use"
