def test_list_roles_includes_the_4_seed_roles(client):
    resp = client.get("/api/roles?page_size=100")
    assert resp.status_code == 200
    names = {r["name"] for r in resp.get_json()["items"]}
    assert {"Admin", "Coordinador", "QM", "Resolutor"}.issubset(names)


def test_create_role_returns_201_with_location(client, unique_name):
    resp = client.post("/api/roles", json={"name": f"Role-{unique_name}", "description": "test role"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/roles/{body['id']}"
    assert body["permissions"] == []


def test_duplicate_role_name_returns_409(client, unique_name):
    name = f"Role-{unique_name}"
    client.post("/api/roles", json={"name": name})
    dup = client.post("/api/roles", json={"name": name})
    assert dup.status_code == 409


def test_replace_role_permissions(client, unique_name):
    role = client.post("/api/roles", json={"name": f"Role-{unique_name}"}).get_json()
    perms = client.get("/api/permissions").get_json()["items"]
    clients_view = next(p["id"] for p in perms if p["module"] == "clients" and p["action"] == "view")

    resp = client.put(f"/api/roles/{role['id']}/permissions", json={"permission_ids": [clients_view]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["permissions"]) == 1
    assert body["permissions"][0]["module"] == "clients"
    assert body["permissions"][0]["action"] == "view"


def test_cannot_deactivate_admin_role(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    admin_role = next(r for r in roles if r["name"] == "Admin")
    resp = client.patch(f"/api/roles/{admin_role['id']}/deactivate")
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "cannot_deactivate_admin_role"


def test_deactivate_role_with_active_users_returns_409_with_count(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    coordinador_role = next(r for r in roles if r["name"] == "Coordinador")
    resp = client.patch(f"/api/roles/{coordinador_role['id']}/deactivate")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "role_in_use"
    assert body["active_users_count"] >= 1


def test_deactivate_then_activate_role_with_no_users_roundtrip(client, unique_name):
    role = client.post("/api/roles", json={"name": f"Role-{unique_name}"}).get_json()
    rid = role["id"]

    deactivated = client.patch(f"/api/roles/{rid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json() == {"id": rid, "active": False}

    activated = client.patch(f"/api/roles/{rid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": rid, "active": True}
