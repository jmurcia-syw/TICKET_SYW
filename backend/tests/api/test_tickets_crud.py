"""US1 — Registro y consulta de tickets (Escenario 2 del quickstart)."""
from datetime import date

# OBS-0011: la fecha de inicio de un proyecto no puede quedar en un mes anterior al actual.
_PROJECT_START = date.today().strftime("%Y-%m-01")


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


def test_create_rejects_invalid_enum(client, ticket_client, ticket_project):
    response = client.post("/api/tickets", json={
        "title": "x", "description": "y", "ticket_type": "bug",
        "priority": "high", "severity": "s2", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"],
    })
    assert response.status_code == 400
    assert "ticket_type" in response.get_json()["message"]


def test_create_ticket_without_client_contact_fails_when_project_has_contacts(
        client, unique_name, ticket_client, ticket_project):
    """spec 038 US4 (FR-018): Ticket obligatorio si el proyecto ya tiene personal Usuario/
    cliente disponible para elegir (contrapartida: test_create_ticket_without_client_contact_
    still_works, en test_tickets_client_contact.py, cubre el proyecto sin ninguno)."""
    contact = client.post("/api/client-contacts", json={
        "email": f"reqcontact.{unique_name}@clienteexterno.com",
        "username": f"reqcontact_{unique_name}", "client_id": ticket_client["id"],
    }).get_json()
    link = client.post(f"/api/projects/{ticket_project['id']}/members", json={"user_id": contact["user_id"]})
    assert link.status_code == 201, link.get_json()

    response = client.post("/api/tickets", json={
        "title": "Ticket sin solicitante", "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
    })
    assert response.status_code == 400
    assert "client_contact_id" in response.get_json()["message"]


def test_create_task_without_client_contact_succeeds_even_with_contacts_available(
        client, unique_name, ticket_client, ticket_project):
    """FR-019: una Tarea nunca exige Usuario/cliente solicitante, a diferencia de un Ticket."""
    contact = client.post("/api/client-contacts", json={
        "email": f"taskcontact.{unique_name}@clienteexterno.com",
        "username": f"taskcontact_{unique_name}", "client_id": ticket_client["id"],
    }).get_json()
    client.post(f"/api/projects/{ticket_project['id']}/members", json={"user_id": contact["user_id"]})

    record_types = client.get("/api/catalogs/record-types").get_json()["items"]
    task_type = next(rt for rt in record_types if rt["name"] == "Tarea")
    response = client.post("/api/tickets", json={
        "title": "Tarea sin solicitante", "description": "Descripción",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
        "record_type_id": task_type["id"],
    })
    assert response.status_code == 201, response.get_json()
    assert response.get_json()["client_contact_id"] is None


def test_create_rejects_project_of_other_client(client, make_ticket, unique_name):
    other = client.post("/api/clients", json={"name": f"Otro Cliente {unique_name}"}).get_json()
    project = client.post("/api/projects", json={
        "client_id": other["id"], "name": f"Proyecto ajeno {unique_name}",
        "start_date": _PROJECT_START,
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


def test_sort_by_priority_uses_real_urgency_not_alphabetical(client, make_ticket, ticket_client):
    """OBS-0028: 'priority' es texto (critical/high/medium/low); el orden debe ser por
    urgencia real (critical primero), no alfabético ('critical' quedaría después de 'high')."""
    low = make_ticket(priority="low", severity="s4")
    critical = make_ticket(priority="critical", severity="s1")
    response = client.get(f"/api/tickets?client_id={ticket_client['id']}&sort=priority&page_size=10")
    assert response.status_code == 200
    ids_in_order = [t["id"] for t in response.get_json()["items"]]
    assert ids_in_order.index(critical["id"]) < ids_in_order.index(low["id"])


def test_default_sort_is_urgency_not_created_at(client, make_ticket, ticket_client):
    """OBS-0028: el orden por defecto (sin pasar `sort`) ya no es '-created_at' — es
    'urgency' (prioridad real, luego severidad como desempate)."""
    low = make_ticket(priority="low", severity="s1")
    high_s3 = make_ticket(priority="high", severity="s3")
    high_s1 = make_ticket(priority="high", severity="s1")
    response = client.get(f"/api/tickets?client_id={ticket_client['id']}&page_size=10")
    ids_in_order = [t["id"] for t in response.get_json()["items"]]
    # high (urgencia 1) antes que low (urgencia 3), independiente de cuál se creó primero
    assert ids_in_order.index(high_s1["id"]) < ids_in_order.index(low["id"])
    # empate en prioridad 'high': severidad s1 (más severo) antes que s3
    assert ids_in_order.index(high_s1["id"]) < ids_in_order.index(high_s3["id"])


def test_sort_by_code_and_status_desc(client, make_ticket, ticket_client):
    """spec 035 (FR-008): `sort=code`/`-code` ordena por número de ticket; `-status` invierte
    el orden alfabético ascendente que ya soportaba `status`."""
    first = make_ticket()
    second = make_ticket()
    response = client.get(f"/api/tickets?client_id={ticket_client['id']}&sort=code&page_size=10")
    ids_in_order = [t["id"] for t in response.get_json()["items"]]
    assert ids_in_order.index(first["id"]) < ids_in_order.index(second["id"])

    response_desc = client.get(f"/api/tickets?client_id={ticket_client['id']}&sort=-code&page_size=10")
    ids_desc = [t["id"] for t in response_desc.get_json()["items"]]
    assert ids_desc.index(second["id"]) < ids_desc.index(first["id"])

    response_status = client.get(f"/api/tickets?client_id={ticket_client['id']}&sort=-status&page_size=10")
    assert response_status.status_code == 200


def test_detail_includes_locked_fields_and_histories(client, make_ticket):
    ticket = make_ticket()
    detail = client.get(f"/api/tickets/{ticket['id']}").get_json()
    assert "status" in detail["locked_fields"]
    assert detail["comments"] == []
    # spec 038 US2 (FR-014): toda Ticket/Tarea nace con 1 transición de auditoría inicial
    # (from_status sentinel "creado"), en vez de un historial vacío.
    assert len(detail["transitions"]) == 1
    assert detail["transitions"][0]["is_creation"] is True
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
