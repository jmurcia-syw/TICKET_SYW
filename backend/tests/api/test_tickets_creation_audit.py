"""spec 038 US2 (FR-014) — entrada de auditoría inicial en el Historial de Estados al crear un
Ticket o una Tarea (`from_status` sentinel `"creado"`, sin tabla nueva)."""


def test_ticket_creation_leaves_initial_audit_transition(client, make_ticket):
    ticket = make_ticket()
    resp = client.get(f"/api/tickets/{ticket['id']}")
    assert resp.status_code == 200
    transitions = resp.get_json()["transitions"]
    assert len(transitions) == 1
    first = transitions[0]
    assert first["from_status"] == "creado"
    assert first["to_status"] == "nuevo"
    assert first["is_creation"] is True
    assert first["comment_id"] is None


def test_task_creation_leaves_initial_audit_transition(client, ticket_client, ticket_project, unique_name):
    record_types = client.get("/api/catalogs/record-types").get_json()["items"]
    task_type = next(rt for rt in record_types if rt["name"] == "Tarea")
    resp = client.post("/api/tickets", json={
        "title": f"Tarea auditoría {unique_name}", "description": "Descripción de la tarea",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
        "record_type_id": task_type["id"],
    })
    assert resp.status_code == 201, resp.get_json()
    task_id = resp.get_json()["id"]

    detail = client.get(f"/api/tickets/{task_id}")
    transitions = detail.get_json()["transitions"]
    assert len(transitions) == 1
    assert transitions[0]["from_status"] == "creado"
    assert transitions[0]["is_creation"] is True


def test_subsequent_transition_is_not_marked_as_creation(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    assign = client.post(f"/api/tickets/{ticket['id']}/assign",
                         json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    assert assign.status_code == 200, assign.get_json()

    detail = client.get(f"/api/tickets/{ticket['id']}")
    transitions = detail.get_json()["transitions"]
    assert len(transitions) == 2
    assert transitions[0]["is_creation"] is True
    assert transitions[1]["is_creation"] is False
    assert transitions[1]["from_status"] == "nuevo"
    assert transitions[1]["to_status"] == "contacto"
