"""spec 038 US1 — permiso `tickets:view_assigned` (Resolutor): listado/detalle acotados a
`assignee_id = resource_id del actor`, sin afectar el acceso global de Admin/Coordinador."""


def _assign(client, ticket_id, resource_id):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": "resolver"})


def test_resolver_with_view_assigned_sees_only_own_tickets(client, make_ticket, ticket_resource, resolver_auth):
    mine_1 = make_ticket()
    mine_2 = make_ticket()
    other = make_ticket()
    assert _assign(client, mine_1["id"], ticket_resource["id"]).status_code == 200
    assert _assign(client, mine_2["id"], ticket_resource["id"]).status_code == 200

    listing = client.get("/api/tickets", headers=resolver_auth)
    assert listing.status_code == 200
    ids = {item["id"] for item in listing.get_json()["items"]}
    assert mine_1["id"] in ids
    assert mine_2["id"] in ids
    assert other["id"] not in ids


def test_admin_still_sees_all_tickets_regardless_of_assignment(client, make_ticket, ticket_resource, ticket_client):
    mine = make_ticket()
    other = make_ticket()
    assert _assign(client, mine["id"], ticket_resource["id"]).status_code == 200

    # Filtra por el Cliente único de este test (fixture `ticket_client`) para no depender del
    # volumen acumulado de tickets de otras pruebas al paginar sin filtro.
    listing = client.get(f"/api/tickets?client_id={ticket_client['id']}")  # fixture `client` = Admin
    ids = {item["id"] for item in listing.get_json()["items"]}
    assert mine["id"] in ids
    assert other["id"] in ids


def test_resolver_detail_of_assigned_ticket_returns_200(client, make_ticket, ticket_resource, resolver_auth):
    mine = make_ticket()
    assert _assign(client, mine["id"], ticket_resource["id"]).status_code == 200

    resp = client.get(f"/api/tickets/{mine['id']}", headers=resolver_auth)
    assert resp.status_code == 200


def test_resolver_detail_of_unassigned_ticket_returns_404(client, make_ticket, resolver_auth):
    other = make_ticket()
    resp = client.get(f"/api/tickets/{other['id']}", headers=resolver_auth)
    assert resp.status_code == 404


def test_resolver_without_resource_profile_gets_empty_list(client, make_ticket, resolver_auth):
    """`resolver_auth` sin el fixture `ticket_resource` — el usuario Resolutor de prueba no
    tiene un Recurso vinculado todavía. La ruta degrada a página vacía, no a error."""
    make_ticket()
    resp = client.get("/api/tickets", headers=resolver_auth)
    assert resp.status_code == 200
    assert resp.get_json()["items"] == []
    assert resp.get_json()["total"] == 0
