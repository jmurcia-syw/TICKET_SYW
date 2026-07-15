"""spec 010, US3 — Personal del Proyecto y subgrupos "Equipo" (estilo Teamwork)."""
import uuid
from datetime import date

import pytest

from backend.domain.entities.user import User
from backend.infra.database import get_db
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.repositories.user_repo import UserRepository

# OBS-0011: la fecha de inicio de un proyecto no puede quedar en un mes anterior al actual.
_PROJECT_START = date.today().strftime("%Y-%m-01")


@pytest.fixture()
def project(client, ticket_client, unique_name):
    """Proyecto activo del cliente de prueba."""
    resp = client.post("/api/projects", json={
        "client_id": ticket_client["id"],
        "name": f"Proyecto Personal {unique_name}",
        "start_date": _PROJECT_START,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture()
def other_project(client, ticket_client, unique_name):
    resp = client.post("/api/projects", json={
        "client_id": ticket_client["id"],
        "name": f"Proyecto Ajeno {unique_name}",
        "start_date": _PROJECT_START,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _assign(client, project_id, user_id):
    return client.post(f"/api/projects/{project_id}/members", json={"user_id": str(user_id)})


def test_assign_user_returns_member_with_derived_role(client, project, resolver_user):
    resp = _assign(client, project["id"], resolver_user.id)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["user_id"] == str(resolver_user.id)
    assert body["role_name"] == "Resolutor"
    assert body["email"] == resolver_user.email


def test_assign_duplicate_returns_409(client, project, resolver_user):
    assert _assign(client, project["id"], resolver_user.id).status_code == 201
    resp = _assign(client, project["id"], resolver_user.id)
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_member"


def test_assign_inactive_user_returns_409(client, app, project, unique_name):
    with app.app_context():
        db = get_db()
        role = RoleRepository(db).get_by_name("Resolutor")
        inactive = UserRepository(db).create(User(
            id=uuid.uuid4(), email=f"inactivo.{unique_name}@sywork.net",
            username=f"inactivo_{unique_name}", role=role, active=False,
        ))
    resp = _assign(client, project["id"], inactive.id)
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "user_inactive"


def test_assign_encargado_and_filter_by_role(client, project, encargado_user, resolver_user):
    assert _assign(client, project["id"], encargado_user.id).status_code == 201
    assert _assign(client, project["id"], resolver_user.id).status_code == 201
    resp = client.get(f"/api/projects/{project['id']}/members?role_name=Usuario/cliente")
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    assert len(items) == 1
    assert items[0]["user_id"] == str(encargado_user.id)
    assert items[0]["role_name"] == "Usuario/cliente"


def test_member_endpoints_404_on_unknown_project(client):
    ghost = uuid.uuid4()
    assert client.get(f"/api/projects/{ghost}/members").status_code == 404
    assert _assign(client, ghost, uuid.uuid4()).status_code == 404


def test_resolutor_cannot_mutate_but_can_view(client, project, resolver_auth, resolver_user):
    resp = client.post(f"/api/projects/{project['id']}/members",
                       json={"user_id": str(resolver_user.id)}, headers=resolver_auth)
    assert resp.status_code == 403
    resp = client.get(f"/api/projects/{project['id']}/members", headers=resolver_auth)
    assert resp.status_code == 200


def test_team_crud_and_duplicate_name(client, project):
    resp = client.post(f"/api/projects/{project['id']}/teams", json={"name": "Infraestructura"})
    assert resp.status_code == 201, resp.get_json()
    team = resp.get_json()
    assert team["member_count"] == 0

    dup = client.post(f"/api/projects/{project['id']}/teams", json={"name": "Infraestructura"})
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "duplicate_name"

    renamed = client.patch(f"/api/project-teams/{team['id']}", json={"name": "Sywork LAB"})
    assert renamed.status_code == 200
    assert renamed.get_json()["name"] == "Sywork LAB"

    assert client.delete(f"/api/project-teams/{team['id']}").status_code == 204
    assert client.patch(f"/api/project-teams/{team['id']}", json={"name": "X"}).status_code == 404


def test_team_members_replace_and_cross_project_rejected(client, project, other_project,
                                                         resolver_user, encargado_user):
    member = _assign(client, project["id"], resolver_user.id).get_json()
    foreign = _assign(client, other_project["id"], encargado_user.id).get_json()
    team = client.post(f"/api/projects/{project['id']}/teams", json={"name": "Equipo X"}).get_json()

    resp = client.put(f"/api/project-teams/{team['id']}/members",
                      json={"member_ids": [member["id"], foreign["id"]]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "member_not_in_project"

    resp = client.put(f"/api/project-teams/{team['id']}/members",
                      json={"member_ids": [member["id"]]})
    assert resp.status_code == 200
    assert resp.get_json()["member_count"] == 1


def test_delete_team_keeps_members_assigned(client, project, resolver_user):
    member = _assign(client, project["id"], resolver_user.id).get_json()
    team = client.post(f"/api/projects/{project['id']}/teams", json={"name": "Efímero"}).get_json()
    client.put(f"/api/project-teams/{team['id']}/members", json={"member_ids": [member["id"]]})

    assert client.delete(f"/api/project-teams/{team['id']}").status_code == 204
    members = client.get(f"/api/projects/{project['id']}/members").get_json()["items"]
    assert any(m["id"] == member["id"] for m in members)


def test_remove_member_cascades_out_of_teams(client, project, resolver_user):
    member = _assign(client, project["id"], resolver_user.id).get_json()
    team = client.post(f"/api/projects/{project['id']}/teams", json={"name": "Cascada"}).get_json()
    client.put(f"/api/project-teams/{team['id']}/members", json={"member_ids": [member["id"]]})

    resp = client.delete(f"/api/projects/{project['id']}/members/{member['id']}")
    assert resp.status_code == 204

    teams = client.get(f"/api/projects/{project['id']}/teams").get_json()["items"]
    target = next(t for t in teams if t["id"] == team["id"])
    assert target["member_count"] == 0
    members = client.get(f"/api/projects/{project['id']}/members").get_json()["items"]
    assert all(m["id"] != member["id"] for m in members)
