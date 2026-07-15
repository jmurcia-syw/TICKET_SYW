import uuid
from datetime import date

# OBS-0011: la fecha de inicio de un proyecto no puede quedar en un mes anterior al actual.
_PROJECT_START = date.today().strftime("%Y-%m-01")


def _make_contact(client, client_id, unique_name, suffix=""):
    resp = client.post("/api/client-contacts", json={
        "email": f"contacto{suffix}.{unique_name}@clienteexterno.com",
        "username": f"contacto{suffix}_{unique_name}",
        "client_id": client_id,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ── Creación (T009/T010, US1) ────────────────────────────────────────────────

def test_create_ticket_with_client_contact_sets_requester(client, unique_name, ticket_client, make_ticket):
    contact = _make_contact(client, ticket_client["id"], unique_name)
    created = make_ticket(client_contact_id=contact["id"])
    assert created["client_contact_id"] == contact["id"]

    detail = client.get(f"/api/tickets/{created['id']}")
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["client_contact_id"] == contact["id"]
    assert body["requester"]["id"] == contact["user_id"]
    assert body["requester"]["is_encargado"] is True


def test_create_ticket_client_contact_from_other_client_returns_409(client, unique_name, ticket_client):
    other_client = client.post("/api/clients", json={"name": f"Otro Cliente {unique_name}"}).get_json()
    contact = _make_contact(client, other_client["id"], unique_name, suffix="_other")
    resp = client.post("/api/tickets", json={
        "title": "Ticket con encargado de otro cliente",
        "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"],
        "client_contact_id": contact["id"],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "client_contact_mismatch"


def test_create_ticket_client_contact_not_found_returns_404(client, ticket_client):
    resp = client.post("/api/tickets", json={
        "title": "Ticket con encargado inexistente",
        "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"],
        "client_contact_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"


def test_create_ticket_without_client_contact_still_works(make_ticket):
    created = make_ticket()
    assert created["client_contact_id"] is None


def test_encargado_self_created_ticket_client_contact_id_stays_null(client, encargado_auth):
    resp = client.post("/api/tickets", json={
        "title": "Ticket de autoservicio", "description": "Descripción",
    }, headers=encargado_auth)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["client_contact_id"] is None
    assert body["requester"]["is_encargado"] is True


def test_resolver_can_list_client_contacts(client, resolver_auth, ticket_client, unique_name):
    _make_contact(client, ticket_client["id"], unique_name, suffix="_forresolver")
    resp = client.get(f"/api/client-contacts?client_id={ticket_client['id']}", headers=resolver_auth)
    assert resp.status_code == 200
    assert resp.get_json()["total"] >= 1


# ── Edición (T015/T016, US2) ─────────────────────────────────────────────────

def test_patch_assigns_client_contact_to_ticket_without_one(client, unique_name, ticket_client, make_ticket):
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch1")
    created = make_ticket()
    assert created["client_contact_id"] is None

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["client_contact_id"] == contact["id"]


def test_patch_reassigns_to_another_client_contact_of_same_client(client, unique_name, ticket_client, make_ticket):
    first = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch2a")
    second = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch2b")
    created = make_ticket(client_contact_id=first["id"])

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": second["id"]})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["client_contact_id"] == second["id"]


def test_patch_client_contact_from_other_client_returns_409(client, unique_name, ticket_client, make_ticket):
    other_client = client.post("/api/clients", json={"name": f"Otro Cliente Patch {unique_name}"}).get_json()
    contact = _make_contact(client, other_client["id"], unique_name, suffix="_patch3")
    created = make_ticket()

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "client_contact_mismatch"


def test_patch_client_contact_on_encargado_ticket_returns_requester_immutable(
        client, encargado_auth, unique_name, ticket_client):
    created = client.post("/api/tickets", json={
        "title": "Ticket autoservicio a editar", "description": "Descripción",
    }, headers=encargado_auth).get_json()
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch4")

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "requester_immutable"


def test_patch_client_contact_locked_when_ticket_cancelled(client, unique_name, ticket_client, make_ticket):
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_patch5")
    created = make_ticket()
    cancelled = client.post(f"/api/tickets/{created['id']}/cancel", json={"body": "Ya no aplica"})
    assert cancelled.status_code == 200, cancelled.get_json()

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": contact["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "field_locked"
    assert "client_contact_id" in resp.get_json()["locked_fields"]


# ── Solicitante por Proyecto (spec 010, US2) ─────────────────────────────────

def _make_project(client, client_id, unique_name, suffix=""):
    resp = client.post("/api/projects", json={
        "client_id": client_id,
        "name": f"Proyecto CC {suffix}{unique_name}",
        "start_date": _PROJECT_START,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _link_to_project(client, project_id, user_id):
    resp = client.post(f"/api/projects/{project_id}/members", json={"user_id": user_id})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_create_ticket_with_contact_linked_to_project_succeeds(client, unique_name, ticket_client, make_ticket):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="ok_")
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_proj_ok")
    _link_to_project(client, project["id"], contact["user_id"])

    created = make_ticket(project_id=project["id"], client_contact_id=contact["id"])
    assert created["client_contact_id"] == contact["id"]


def test_create_ticket_with_contact_not_in_project_returns_409(client, unique_name, ticket_client):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="no_")
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_proj_no")
    # mismo Cliente, pero SIN vincular al proyecto
    resp = client.post("/api/tickets", json={
        "title": "Solicitante fuera del proyecto", "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"],
        "project_id": project["id"],
        "client_contact_id": contact["id"],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "contact_not_in_project"


def test_create_ticket_with_contact_and_no_project_keeps_client_rule(client, unique_name, ticket_client, make_ticket):
    """Sin proyecto no hay chequeo de membresía — comportamiento spec 007 intacto."""
    contact = _make_contact(client, ticket_client["id"], unique_name, suffix="_noproj")
    created = make_ticket(client_contact_id=contact["id"])
    assert created["client_contact_id"] == contact["id"]


def test_patch_contact_not_in_ticket_project_returns_409(client, unique_name, ticket_client, make_ticket):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="patch_")
    linked = _make_contact(client, ticket_client["id"], unique_name, suffix="_p_link")
    unlinked = _make_contact(client, ticket_client["id"], unique_name, suffix="_p_unlink")
    _link_to_project(client, project["id"], linked["user_id"])
    created = make_ticket(project_id=project["id"], client_contact_id=linked["id"])

    resp = client.patch(f"/api/tickets/{created['id']}", json={"client_contact_id": unlinked["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "contact_not_in_project"


def test_list_client_contacts_filtered_by_project(client, unique_name, ticket_client):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="filter_")
    linked = _make_contact(client, ticket_client["id"], unique_name, suffix="_f_link")
    _make_contact(client, ticket_client["id"], unique_name, suffix="_f_unlink")
    _link_to_project(client, project["id"], linked["user_id"])

    resp = client.get(f"/api/client-contacts?project_id={project['id']}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == linked["id"]


# ── Autoservicio acotado a proyectos vinculados (spec 010, FR-007) ───────────

def test_encargado_selfservice_with_linked_project_succeeds(client, encargado_auth, encargado_user,
                                                            unique_name, ticket_client):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="self_ok_")
    _link_to_project(client, project["id"], str(encargado_user.id))

    resp = client.post("/api/tickets", json={
        "title": "Autoservicio en mi proyecto", "description": "Descripción",
        "project_id": project["id"],
    }, headers=encargado_auth)
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["project"]["id"] == project["id"]


def test_encargado_selfservice_with_unlinked_project_returns_409(client, encargado_auth,
                                                                 unique_name, ticket_client):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="self_no_")

    resp = client.post("/api/tickets", json={
        "title": "Autoservicio en proyecto ajeno", "description": "Descripción",
        "project_id": project["id"],
    }, headers=encargado_auth)
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "project_not_assigned"


def test_me_projects_returns_only_own_memberships(client, encargado_auth, encargado_user,
                                                  unique_name, ticket_client):
    linked = _make_project(client, ticket_client["id"], unique_name, suffix="mine_")
    _make_project(client, ticket_client["id"], unique_name, suffix="foreign_")
    _link_to_project(client, linked["id"], str(encargado_user.id))

    resp = client.get("/api/client-contacts/me/projects", headers=encargado_auth)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == linked["id"]


# ── Alta por Proyecto y filtros de listado (spec 010, ajuste post-implementación) ──

def test_create_contact_with_project_derives_client_and_membership(client, unique_name, ticket_client):
    project = _make_project(client, ticket_client["id"], unique_name, suffix="alta_")
    resp = client.post("/api/client-contacts", json={
        "email": f"porproyecto.{unique_name}@clienteexterno.com",
        "username": f"porproyecto_{unique_name}",
        "project_id": project["id"],
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["client_id"] == ticket_client["id"]  # Cliente derivado del Proyecto

    members = client.get(f"/api/projects/{project['id']}/members").get_json()["items"]
    assert any(m["user_id"] == body["user_id"] for m in members)  # membresía automática

    listed = client.get(f"/api/client-contacts?project_id={project['id']}").get_json()
    contact = next(c for c in listed["items"] if c["user_id"] == body["user_id"])
    assert [p["id"] for p in contact["projects"]] == [project["id"]]


def test_create_contact_without_project_or_client_returns_400(client, unique_name):
    resp = client.post("/api/client-contacts", json={
        "email": f"sinvinculo.{unique_name}@clienteexterno.com",
        "username": f"sinvinculo_{unique_name}",
    })
    assert resp.status_code == 400


def test_list_contacts_filters_by_email_and_username(client, unique_name, ticket_client):
    target = _make_contact(client, ticket_client["id"], unique_name, suffix="_filtrado")
    _make_contact(client, ticket_client["id"], unique_name, suffix="_otro")

    by_email = client.get(f"/api/client-contacts?email=contacto_filtrado.{unique_name}").get_json()
    assert by_email["total"] == 1
    assert by_email["items"][0]["id"] == target["id"]

    by_username = client.get(f"/api/client-contacts?username=contacto_filtrado_{unique_name}").get_json()
    assert by_username["total"] == 1
    assert by_username["items"][0]["id"] == target["id"]

    combined = client.get(
        f"/api/client-contacts?client_id={ticket_client['id']}&email=filtrado.{unique_name}").get_json()
    assert combined["total"] == 1
