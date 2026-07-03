"""US2 — Triage Push y Gold Standard Dataset (Escenario 3 del quickstart)."""


def _assign(client, ticket_id, resource_id, mode="resolver"):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": mode})


def test_assign_resolver_moves_to_contacto(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    response = _assign(client, ticket["id"], ticket_resource["id"])
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["ticket"]["status"] == "contacto"
    assert data["ticket"]["assignee"]["id"] == ticket_resource["id"]
    # comentario automático "Asignado"
    comments = data["ticket"]["comments"]
    assert len(comments) == 1
    assert comments[0]["comment_type"] == "asignado"
    assert comments[0]["is_automatic"] is True
    # Gold Standard Dataset (FR-019)
    context = data["assignment"]["context"]
    assert set(context) == {"assignee_skills", "assignee_open_tickets",
                            "ticket_priority", "ticket_severity"}
    assert context["ticket_priority"] == "high"


def test_assign_qm_moves_to_pre_analisis(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    response = _assign(client, ticket["id"], ticket_resource["id"], mode="pre_analysis")
    assert response.status_code == 200
    assert response.get_json()["ticket"]["status"] == "pre_analisis"


def test_reassign_from_pre_analisis_keeps_history(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"], mode="pre_analysis")
    response = _assign(client, ticket["id"], ticket_resource["id"], mode="resolver")
    assert response.status_code == 200
    detail = client.get(f"/api/tickets/{ticket['id']}").get_json()
    assert detail["status"] == "contacto"
    assert len(detail["assignments"]) == 2  # append-only, nunca pierde entradas


def test_assign_to_inactive_resource_rejected(client, make_ticket, ticket_resource):
    client.patch(f"/api/resources/{ticket_resource['id']}/deactivate")
    ticket = make_ticket()
    response = _assign(client, ticket["id"], ticket_resource["id"])
    assert response.status_code == 400
    assert "inactivo" in response.get_json()["message"]
    client.patch(f"/api/resources/{ticket_resource['id']}/activate")


def test_assign_from_invalid_state_is_409(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])  # → contacto
    response = _assign(client, ticket["id"], ticket_resource["id"], mode="pre_analysis")
    assert response.status_code == 409
    assert "Acciones válidas" in response.get_json()["message"]


def test_assignee_receives_notification(client, make_ticket, ticket_resource, resolver_auth, anon_client):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    response = anon_client.get("/api/notifications?unread=true", headers=resolver_auth)
    assert response.status_code == 200
    data = response.get_json()
    assert data["unread_count"] >= 1
    assert any(n["event_type"] == "assigned" and n["ticket"]["id"] == ticket["id"]
               for n in data["items"])
