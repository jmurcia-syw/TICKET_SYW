"""Escenario 1 del quickstart (FR-022): enforcement JWT + permisos en toda la API."""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_masters_require_token(anon_client):
    for path in ("/api/clients", "/api/projects", "/api/resources", "/api/skills",
                 "/api/users", "/api/roles", "/api/permissions"):
        response = anon_client.get(path)
        assert response.status_code == 401, f"{path} devolvió {response.status_code}"


def test_tickets_require_token(anon_client):
    assert anon_client.get("/api/tickets").status_code == 401


def test_public_routes_stay_public(anon_client):
    assert anon_client.get("/health/").status_code in (200, 503)
    # login inválido responde 400/401, nunca 500 ni redirect a auth
    response = anon_client.post("/api/auth/login", json={})
    assert response.status_code in (400, 401)


def test_admin_token_grants_access(client):
    # `client` inyecta el token de Admin por defecto
    assert client.get("/api/clients").status_code == 200
    assert client.get("/api/roles").status_code == 200


def test_resolver_can_view_but_not_create_clients(anon_client, resolver_token):
    assert anon_client.get("/api/clients", headers=_auth(resolver_token)).status_code == 200
    response = anon_client.post("/api/clients", headers=_auth(resolver_token),
                                json={"name": "No debería crearse"})
    assert response.status_code == 403
    assert "message" in response.get_json()
    assert "No debería" not in response.get_data(as_text=True)  # payload genérico (FR-023)


def test_coordinator_cannot_manage_roles(anon_client, coordinator_token):
    response = anon_client.post("/api/roles", headers=_auth(coordinator_token),
                                json={"name": "RolPirata"})
    assert response.status_code == 403


def test_qm_cannot_cancel_tickets_permission_missing(anon_client, qm_token):
    # QM no tiene tickets:cancel (seed 011) — el 403 llega del decorador aunque el
    # ticket no exista (el permiso se evalúa antes)
    response = anon_client.post(
        "/api/tickets/00000000-0000-0000-0000-000000000001/cancel",
        headers=_auth(qm_token), json={"body": "x"})
    assert response.status_code == 403


def test_garbage_token_is_401_not_500(anon_client):
    response = anon_client.get("/api/clients", headers=_auth("no-es-un-jwt"))
    assert response.status_code == 401
