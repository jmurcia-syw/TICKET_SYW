def test_list_permissions_includes_the_24_seed_permissions(client):
    resp = client.get("/api/permissions")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] >= 24
    modules = {p["module"] for p in body["items"]}
    assert {"clients", "projects", "resources", "skills", "users", "roles"}.issubset(modules)


def test_create_permission_returns_201_with_location(client, unique_name):
    resp = client.post("/api/permissions", json={"module": f"mod_{unique_name}", "action": "view"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/permissions/{body['id']}"


def test_duplicate_module_action_returns_409(client, unique_name):
    payload = {"module": f"mod_{unique_name}", "action": "view"}
    client.post("/api/permissions", json=payload)
    dup = client.post("/api/permissions", json=payload)
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "module_action_duplicate"


def test_delete_unused_permission(client, unique_name):
    created = client.post("/api/permissions", json={"module": f"mod_{unique_name}", "action": "edit"}).get_json()
    resp = client.delete(f"/api/permissions/{created['id']}")
    assert resp.status_code == 204


def test_delete_permission_assigned_to_a_role_returns_409(client, unique_name):
    permission = client.post("/api/permissions", json={"module": f"mod_{unique_name}", "action": "create"}).get_json()
    role = client.post("/api/roles", json={"name": f"Role-{unique_name}"}).get_json()
    client.put(f"/api/roles/{role['id']}/permissions", json={"permission_ids": [permission["id"]]})

    resp = client.delete(f"/api/permissions/{permission['id']}")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "permission_in_use"
    assert body["role_count"] == 1
