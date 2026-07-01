def test_list_users(client):
    resp = client.get("/api/users?page_size=100")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "items" in body and "total" in body


def test_get_unknown_user_returns_404(client):
    resp = client.get("/api/users/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404


def test_get_resolver_user(client, resolver_user):
    resp = client.get(f"/api/users/{resolver_user.id}")
    assert resp.status_code == 200
    assert resp.get_json()["role"]["name"] == "Resolutor"


def test_change_role(client, resolver_user):
    coordinador_role = next(
        r for r in client.get("/api/roles?page_size=100").get_json()["items"] if r["name"] == "Coordinador"
    )
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role_id": coordinador_role["id"]})
    assert resp.status_code == 200
    assert resp.get_json()["role"]["name"] == "Coordinador"


def test_change_role_invalid_uuid_returns_400(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role_id": "not-a-uuid"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_change_role_unknown_role_returns_404(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role_id": "00000000-0000-0000-0000-000000000099"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "role_not_found"


def test_deactivate_then_activate_user_returns_minimal_shape(client, resolver_user):
    """Regression: UserActivate used to return the full user object, mismatching its
    own documented UserStatusResult schema and the {id, active} shape every other
    maestro's /activate returns."""
    uid = str(resolver_user.id)

    deactivated = client.patch(f"/api/users/{uid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json() == {"id": uid, "active": False}

    activated = client.patch(f"/api/users/{uid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": uid, "active": True}


def test_reactivating_already_active_user_returns_409(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/activate")
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_active"
