def test_create_client_returns_201_with_location_header(client, unique_name):
    resp = client.post("/api/clients", json={"name": f"Client-{unique_name}"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/clients/{body['id']}"
    assert body["active"] is True


def test_get_and_patch_client(client, unique_name):
    created = client.post("/api/clients", json={"name": f"Client-{unique_name}"}).get_json()
    cid = created["id"]

    got = client.get(f"/api/clients/{cid}")
    assert got.status_code == 200
    assert got.get_json()["name"] == f"Client-{unique_name}"

    patched = client.patch(f"/api/clients/{cid}", json={"notes": "updated via test"})
    assert patched.status_code == 200
    assert patched.get_json()["notes"] == "updated via test"


def test_create_client_name_only_symbols_rejected(client):
    """OBS-0014: nombre sin ningún alfanumérico (solo símbolos/emojis) es rechazado."""
    resp = client.post("/api/clients", json={"name": "!@#$%^&*"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_client_name_too_long_rejected(client):
    """OBS-0014: nombre de más de 120 caracteres es rechazado."""
    resp = client.post("/api/clients", json={"name": "A" * 121})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_client_invalid_phone_rejected(client, unique_name):
    """OBS-0007/OBS-0016: contact_phone debe ser E.164; letras o formato libre se rechazan."""
    resp = client.post("/api/clients", json={"name": f"Client-{unique_name}", "contact_phone": "abc123"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_client_valid_e164_phone_accepted(client, unique_name):
    resp = client.post("/api/clients", json={"name": f"Client-{unique_name}", "contact_phone": "+573001234567"})
    assert resp.status_code == 201
    assert resp.get_json()["contact_phone"] == "+573001234567"


def test_duplicate_client_name_returns_409(client, unique_name):
    name = f"Client-{unique_name}"
    client.post("/api/clients", json={"name": name})
    dup = client.post("/api/clients", json={"name": name})
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "name_duplicate"


def test_deactivate_then_activate_client_roundtrip(client, unique_name):
    """Regression: ClientRepository.set_active was missing, so /activate returned 500."""
    created = client.post("/api/clients", json={"name": f"Client-{unique_name}"}).get_json()
    cid = created["id"]

    deactivated = client.patch(f"/api/clients/{cid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json()["active"] is False

    activated = client.patch(f"/api/clients/{cid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": cid, "active": True}


def test_invalid_uuid_returns_400(client):
    resp = client.get("/api/clients/not-a-uuid")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_unknown_client_returns_404(client):
    resp = client.get("/api/clients/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"
