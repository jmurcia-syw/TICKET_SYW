"""spec 038 US1 — `GET /resources/{id}/work-schedule` acotado al propio recurso para actores
sin `resources:edit` (Resolutor): el Calendario de Equipo deja de exponer la franja horaria de
otros recursos a quien solo tiene `resources:view`, sin afectar a Admin/Coordinador/QM."""


def test_resolver_can_view_own_work_schedule(client, ticket_resource, resolver_auth):
    resp = client.get(f"/api/resources/{ticket_resource['id']}/work-schedule", headers=resolver_auth)
    assert resp.status_code == 200


def test_resolver_cannot_view_other_resource_work_schedule(client, unique_name, resolver_auth):
    other = client.post("/api/resources", json={
        "full_name": f"Otro Recurso {unique_name}",
        "email": f"otro.{unique_name}@sywork.net",
    })
    assert other.status_code == 201, other.get_json()

    resp = client.get(f"/api/resources/{other.get_json()['id']}/work-schedule", headers=resolver_auth)
    assert resp.status_code == 403


def test_admin_can_view_any_resource_work_schedule(client, ticket_resource):
    resp = client.get(f"/api/resources/{ticket_resource['id']}/work-schedule")  # fixture `client` = Admin
    assert resp.status_code == 200
