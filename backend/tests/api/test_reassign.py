"""Reasignación de resolutor (spec 023) — endpoint independiente de /assign."""


def _second_resource(client, unique_name):
    response = client.post("/api/resources", json={
        "full_name": f"Segundo Resolutor {unique_name}",
        "email": f"segundo.tk.{unique_name}@sywork.net",
    })
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _reassign(client, ticket_id, assignee_id, reason=None):
    payload = {"assignee_id": assignee_id}
    if reason is not None:
        payload["reason"] = reason
    return client.post(f"/api/tickets/{ticket_id}/reassign", json=payload)


def test_reassign_success_updates_assignee_and_history(client, make_ticket, ticket_resource, unique_name):
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/assign",
               json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    second = _second_resource(client, unique_name)

    response = _reassign(client, ticket["id"], second["id"], reason="Escalamiento por complejidad")
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["ticket"]["assignee"]["id"] == second["id"]
    assert data["ticket"]["status"] == "contacto"  # no toca el FSM

    reassignment = data["reassignment"]
    assert reassignment["previous_assignee_id"] == ticket_resource["id"]
    assert reassignment["previous_assignee_name"] == ticket_resource["full_name"]
    assert reassignment["new_assignee_id"] == second["id"]
    assert reassignment["reason"] == "Escalamiento por complejidad"

    detail = client.get(f"/api/tickets/{ticket['id']}").get_json()
    assert len(detail["reassignments"]) == 1


def test_reassign_same_assignee_is_rejected(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/assign",
               json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    response = _reassign(client, ticket["id"], ticket_resource["id"])
    assert response.status_code == 400
    detail = client.get(f"/api/tickets/{ticket['id']}").get_json()
    assert len(detail["reassignments"]) == 0


def test_reassign_terminal_ticket_is_rejected(client, make_ticket, ticket_resource):
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/cancel", json={"body": "Duplicado"})
    response = _reassign(client, ticket["id"], ticket_resource["id"])
    assert response.status_code == 409
    assert response.get_json()["error"] == "ticket_closed"


def test_reassign_without_permission_is_403(client, make_ticket, ticket_resource,
                                            resolver_auth, anon_client):
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/assign",
               json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    response = anon_client.post(f"/api/tickets/{ticket['id']}/reassign",
                                json={"assignee_id": ticket_resource["id"]},
                                headers=resolver_auth)
    assert response.status_code == 403
