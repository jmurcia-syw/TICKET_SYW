import uuid


def _make_contact(client, client_id, unique_name, suffix=""):
    resp = client.post("/api/client-contacts", json={
        "email": f"contacto{suffix}.{unique_name}@clienteexterno.com",
        "username": f"contacto{suffix}_{unique_name}",
        "client_id": client_id,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ── Creación (T009/T010, US1) ────────────────────────────────────────────────

def test_create_ticket_with_client_contact_sets_requester(client, unique_name, ticket_client, make_ticket):
    contact = _make_contact(client, ticket_client["id"], unique_name)
    created = make_ticket(client_contact_id=contact["id"])
    assert created["client_contact_id"] == contact["id"]

    detail = client.get(f"/api/tickets/{created['id']}")
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["client_contact_id"] == contact["id"]
    assert body["requester"]["id"] == contact["user_id"]
    assert body["requester"]["is_encargado"] is True


def test_create_ticket_client_contact_from_other_client_returns_409(client, unique_name, ticket_client):
    other_client = client.post("/api/clients", json={"name": f"Otro Cliente {unique_name}"}).get_json()
    contact = _make_contact(client, other_client["id"], unique_name, suffix="_other")
    resp = client.post("/api/tickets", json={
        "title": "Ticket con encargado de otro cliente",
        "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"],
        "client_contact_id": contact["id"],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "client_contact_mismatch"


def test_create_ticket_client_contact_not_found_returns_404(client, ticket_client):
    resp = client.post("/api/tickets", json={
        "title": "Ticket con encargado inexistente",
        "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"],
        "client_contact_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"


def test_create_ticket_without_client_contact_still_works(make_ticket):
    created = make_ticket()
    assert created["client_contact_id"] is None


def test_encargado_self_created_ticket_client_contact_id_stays_null(client, encargado_auth):
    resp = client.post("/api/tickets", json={
        "title": "Ticket de autoservicio", "description": "Descripción",
    }, headers=encargado_auth)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["client_contact_id"] is None
    assert body["requester"]["is_encargado"] is True


def test_resolver_can_list_client_contacts(client, resolver_auth, ticket_client, unique_name):
    _make_contact(client, ticket_client["id"], unique_name, suffix="_forresolver")
    resp = client.get(f"/api/client-contacts?client_id={ticket_client['id']}", headers=resolver_auth)
    assert resp.status_code == 200
    assert resp.get_json()["total"] >= 1


# ── Edición (T015/T016, US2) ─────────────────────────────────────────────────

def test_patch_assigns_client_contact_to_ticket_without_one(client, unique_name, ticket_client, make_ticket):
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch1")
    created = make_ticket()
    assert created["client_contact_id"] is None

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["client_contact_id"] == contact["id"]


def test_patch_reassigns_to_another_client_contact_of_same_client(client, unique_name, ticket_client, make_ticket):
    first = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch2a")
    second = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch2b")
    created = make_ticket(client_contact_id=first["id"])

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": second["id"]})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["client_contact_id"] == second["id"]


def test_patch_client_contact_from_other_client_returns_409(client, unique_name, ticket_client, make_ticket):
    other_client = client.post("/api/clients", json={"name": f"Otro Cliente Patch {unique_name}"}).get_json()
    contact = _make_contact(client, other_client["id"], unique_name, suffix="_patch3")
    created = make_ticket()

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "client_contact_mismatch"


def test_patch_client_contact_on_encargado_ticket_returns_requester_immutable(
        client, encargado_auth, unique_name, ticket_client):
    created = client.post("/api/tickets", json={
        "title": "Ticket autoservicio a editar", "description": "Descripción",
    }, headers=encargado_auth).get_json()
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch4")

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "requester_immutable"


def test_patch_client_contact_locked_when_ticket_cancelled(client, unique_name, ticket_client, make_ticket):
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch5")
    created = make_ticket()
    cancelled = client.post(f"/api/tickets/{created['id']}/cancel", json={"body": "Ya no aplica"})
    assert cancelled.status_code == 200, cancelled.get_json()

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "field_locked"
    assert "client_contact_id" in resp.get_json()["locked_fields"]
