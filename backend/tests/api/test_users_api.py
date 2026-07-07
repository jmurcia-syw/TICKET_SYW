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


def _resolutor_role_id(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    return next(r["id"] for r in roles if r["name"] == "Resolutor")


def test_create_user_returns_201_with_provisional_password(client, unique_name):
    role_id = _resolutor_role_id(client)
    resp = client.post("/api/users", json={
        "email": f"nuevo.{unique_name}@sywork.net",
        "username": f"nuevo_{unique_name}",
        "role_id": role_id,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/users/{body['user']['id']}"
    assert body["user"]["email"] == f"nuevo.{unique_name}@sywork.net"
    assert body["user"]["role"]["name"] == "Resolutor"
    assert isinstance(body["provisional_password"], str) and len(body["provisional_password"]) > 8
    assert "password_hash" not in body["user"]

    # La contraseña provisional permite iniciar sesion de inmediato
    login = client.post("/api/auth/login", json={
        "username_or_email": f"nuevo_{unique_name}",
        "password": body["provisional_password"],
    })
    assert login.status_code == 200


def test_create_user_invalid_email_domain_returns_400(client, unique_name):
    role_id = _resolutor_role_id(client)
    resp = client.post("/api/users", json={
        "email": f"nuevo.{unique_name}@gmail.com",
        "username": f"nuevo_{unique_name}",
        "role_id": role_id,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_email_domain"


def test_create_user_duplicate_email_returns_409(client, unique_name, resolver_user):
    role_id = _resolutor_role_id(client)
    resp = client.post("/api/users", json={
        "email": resolver_user.email,
        "username": f"otro_{unique_name}",
        "role_id": role_id,
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "email_duplicate"


def test_create_user_duplicate_username_returns_409(client, unique_name, resolver_user):
    role_id = _resolutor_role_id(client)
    resp = client.post("/api/users", json={
        "email": f"otro.{unique_name}@sywork.net",
        "username": resolver_user.username,
        "role_id": role_id,
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "username_duplicate"


def test_create_user_unknown_role_returns_404(client, unique_name):
    resp = client.post("/api/users", json={
        "email": f"nuevo.{unique_name}@sywork.net",
        "username": f"nuevo_{unique_name}",
        "role_id": "00000000-0000-0000-0000-000000000099",
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "role_not_found"


def test_create_user_missing_fields_returns_400(client):
    resp = client.post("/api/users", json={"email": "a@sywork.net"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_reset_password_returns_new_working_password(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/reset-password")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == str(resolver_user.id)
    assert isinstance(body["provisional_password"], str) and len(body["provisional_password"]) > 8

    login = client.post("/api/auth/login", json={
        "username_or_email": resolver_user.username,
        "password": body["provisional_password"],
    })
    assert login.status_code == 200


def test_reset_password_unknown_user_returns_404(client):
    resp = client.patch("/api/users/00000000-0000-0000-0000-000000000099/reset-password")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"


def test_reset_password_invalid_uuid_returns_400(client):
    resp = client.patch("/api/users/not-a-uuid/reset-password")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"
