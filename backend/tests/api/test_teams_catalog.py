"""Catálogo administrable "teams" (OBS-0024): reemplaza el input libre de "Equipo" en Recursos."""


def test_teams_catalog_seeded(client):
    response = client.get("/api/catalogs/teams")
    assert response.status_code == 200
    names = {item["name"] for item in response.get_json()["items"]}
    assert {"Oracle EBS", "Oracle Fusion", "Data & Analytics", "Infraestructura", "Otro"} <= names


def test_create_team_catalog_value(client, unique_name):
    resp = client.post("/api/catalogs/teams", json={"name": f"Equipo {unique_name}"})
    assert resp.status_code == 201
    assert resp.get_json()["active"] is True


def test_deactivate_team_catalog_value_not_blocked_by_tickets(client, unique_name):
    """'teams' no está ligado a tickets (a diferencia de tools/processes/etc.) — desactivar no
    debe fallar con KeyError ni exigir el chequeo de uso en tickets."""
    created = client.post("/api/catalogs/teams", json={"name": f"Equipo {unique_name}"}).get_json()
    resp = client.patch(f"/api/catalogs/teams/{created['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.get_json()["active"] is False


def test_create_resource_with_team_from_catalog(client, unique_name):
    resp = client.post("/api/resources", json={
        "full_name": f"Resource {unique_name}", "email": f"res.{unique_name}@sywork.net",
        "team": "Oracle Fusion",
    })
    assert resp.status_code == 201
    assert resp.get_json()["team"] == "Oracle Fusion"
