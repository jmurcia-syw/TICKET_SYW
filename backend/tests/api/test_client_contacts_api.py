def test_create_client_contact_returns_201(client, unique_name, ticket_client):
    resp = client.post("/api/client-contacts", json={
        "email": f"contacto.{unique_name}@clienteexterno.com",
        "username": f"contacto_{unique_name}",
        "client_id": ticket_client["id"],
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["client_id"] == ticket_client["id"]
    assert body["provisional_password"]


def test_create_client_contact_duplicate_email_returns_409(client, unique_name, ticket_client):
    email = f"dup.{unique_name}@clienteexterno.com"
    first = client.post("/api/client-contacts", json={
        "email": email, "username": f"dup_a_{unique_name}", "client_id": ticket_client["id"],
    })
    assert first.status_code == 201, first.get_json()

    second = client.post("/api/client-contacts", json={
        "email": email, "username": f"dup_b_{unique_name}", "client_id": ticket_client["id"],
    })
    assert second.status_code == 409
    assert second.get_json()["error"] == "email_in_use"


def test_create_client_contact_client_not_found_returns_404(client, unique_name):
    import uuid
    resp = client.post("/api/client-contacts", json={
        "email": f"nf.{unique_name}@clienteexterno.com",
        "username": f"nf_{unique_name}",
        "client_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "client_not_found"


def test_create_client_contact_inactive_client_returns_404(client, unique_name, ticket_client):
    deactivated = client.patch(f"/api/clients/{ticket_client['id']}/deactivate")
    assert deactivated.status_code == 200

    resp = client.post("/api/client-contacts", json={
        "email": f"inactive.{unique_name}@clienteexterno.com",
        "username": f"inactive_{unique_name}",
        "client_id": ticket_client["id"],
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "client_not_found"


def test_list_client_contacts_filters_by_client(client, unique_name, ticket_client):
    client.post("/api/client-contacts", json={
        "email": f"list.{unique_name}@clienteexterno.com",
        "username": f"list_{unique_name}",
        "client_id": ticket_client["id"],
    })
    resp = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] >= 1
    assert all(item["client_id"] == ticket_client["id"] for item in body["items"])


def test_create_client_contact_forbidden_for_resolver(client, unique_name, ticket_client, resolver_auth):
    resp = client.post("/api/client-contacts", json={
        "email": f"forbidden.{unique_name}@clienteexterno.com",
        "username": f"forbidden_{unique_name}",
        "client_id": ticket_client["id"],
    }, headers=resolver_auth)
    assert resp.status_code == 403
