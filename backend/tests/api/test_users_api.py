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
    assert resp.get_json()["role"] == "resolver"


def test_change_role(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role": "coordinator"})
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "coordinator"


def test_change_role_invalid_value_returns_400(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role": "not-a-role"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_role"


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
