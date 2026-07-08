def test_encargado_create_ticket_uses_simplified_payload_and_own_client(client, encargado_auth, ticket_client):
    resp = client.post("/api/tickets", json={
        "title": "No puedo acceder al portal",
        "description": "Me sale error 500 al iniciar sesión",
    }, headers=encargado_auth)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["client"]["id"] == ticket_client["id"]
    assert body["ticket_type"] == "incident"
    assert body["priority"] == "medium"
    assert body["severity"] == "s3"
    assert body["requester"]["is_encargado"] is True


def test_encargado_create_ticket_ignores_extra_fields(client, encargado_auth):
    resp = client.post("/api/tickets", json={
        "title": "Otro problema", "description": "Detalle del problema",
        "ticket_type": "evolutive", "priority": "critical", "severity": "s1",
        "client_id": "00000000-0000-0000-0000-000000000000",
    }, headers=encargado_auth)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["ticket_type"] == "incident"
    assert body["priority"] == "medium"
    assert body["severity"] == "s3"


def test_encargado_create_ticket_requires_title_and_description(client, encargado_auth):
    resp = client.post("/api/tickets", json={"title": "Solo título"}, headers=encargado_auth)
    assert resp.status_code == 400


def test_encargado_only_sees_own_tickets_in_list(client, encargado_auth, make_ticket):
    other_ticket = make_ticket()  # creado por Admin, no por el Encargado
    own = client.post("/api/tickets", json={
        "title": "Mi propio ticket", "description": "Descripción de mi ticket",
    }, headers=encargado_auth)
    assert own.status_code == 201, own.get_json()
    own_id = own.get_json()["id"]

    listing = client.get("/api/tickets", headers=encargado_auth)
    assert listing.status_code == 200
    ids = {item["id"] for item in listing.get_json()["items"]}
    assert own_id in ids
    assert other_ticket["id"] not in ids


def test_encargado_detail_of_others_ticket_returns_404(client, encargado_auth, make_ticket):
    other_ticket = make_ticket()
    resp = client.get(f"/api/tickets/{other_ticket['id']}", headers=encargado_auth)
    assert resp.status_code == 404


def test_encargado_detail_of_own_ticket_returns_200_with_requester(client, encargado_auth):
    created = client.post("/api/tickets", json={
        "title": "Ticket propio detalle", "description": "Descripción",
    }, headers=encargado_auth)
    ticket_id = created.get_json()["id"]

    resp = client.get(f"/api/tickets/{ticket_id}", headers=encargado_auth)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["requester"]["is_encargado"] is True


def test_admin_still_sees_all_tickets_including_encargado_ones(client, encargado_auth, make_ticket):
    other_ticket = make_ticket()
    own = client.post("/api/tickets", json={
        "title": "Ticket de encargado visible para admin", "description": "Descripción",
    }, headers=encargado_auth)
    own_id = own.get_json()["id"]

    listing = client.get("/api/tickets")  # `client` fixture = Admin token
    ids = {item["id"] for item in listing.get_json()["items"]}
    assert other_ticket["id"] in ids
    assert own_id in ids

    detail = client.get(f"/api/tickets/{own_id}")
    assert detail.status_code == 200
    assert detail.get_json()["requester"]["is_encargado"] is True


def test_encargado_can_list_own_notifications(client, encargado_auth):
    """Regression: notifications.py gated on tickets:view only, which Encargado never has
    (only tickets:view_own) — broke the notification bell for this role with a 403."""
    resp = client.get("/api/notifications?unread=false&page=1&page_size=10", headers=encargado_auth)
    assert resp.status_code == 200
    assert resp.get_json()["items"] == []


def test_encargado_without_client_contact_gets_409(client, unique_name):
    from flask_jwt_extended import create_access_token
    from backend.domain.entities.user import User
    from backend.infra.database import get_db
    from backend.infra.repositories.role_repo import RoleRepository
    from backend.infra.repositories.user_repo import UserRepository
    import uuid

    app = client.application
    with app.app_context():
        role = RoleRepository(get_db()).get_by_name("Encargado")
        orphan = UserRepository(get_db()).create(User(
            id=uuid.uuid4(), email=f"orphan.{unique_name}@clienteexterno.com",
            username=f"orphan_{unique_name}", role=role,
        ))
        token = create_access_token(identity=str(orphan.id))

    resp = client.post("/api/tickets", json={
        "title": "Sin cliente asociado", "description": "Descripción",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "no_client_contact"
