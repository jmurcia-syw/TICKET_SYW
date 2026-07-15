"""spec 015 — Encargado (Usuario/cliente) en múltiples Proyectos.
spec 016 — Corregir el Cliente de un Usuario/cliente con 0 Proyectos asignados.

Fixtures acotados al flujo de la feature (Clientes y Proyectos) — sin usuarios Resolutor
adicionales ni disparo del correo de reseteo/reenvío de contraseña (la contraseña provisional se
valida en la respuesta JSON del alta, como ya hacía spec 010/007).
"""
import uuid

import pytest


@pytest.fixture()
def other_client(client, unique_name):
    """Segundo Cliente (maestro) de prueba, distinto de ticket_client."""
    resp = client.post("/api/clients", json={"name": f"Cliente Ajeno {unique_name}"})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture()
def project_a(client, ticket_client, unique_name):
    resp = client.post("/api/projects", json={
        "client_id": ticket_client["id"],
        "name": f"Proyecto A {unique_name}",
        "start_date": "2026-01-15",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture()
def project_b(client, ticket_client, unique_name):
    resp = client.post("/api/projects", json={
        "client_id": ticket_client["id"],
        "name": f"Proyecto B {unique_name}",
        "start_date": "2026-01-15",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture()
def project_other_client(client, other_client, unique_name):
    resp = client.post("/api/projects", json={
        "client_id": other_client["id"],
        "name": f"Proyecto Otro Cliente {unique_name}",
        "start_date": "2026-01-15",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ── US1: alta con varios Proyectos ──────────────────────────────────────────

def test_create_with_two_projects_same_client_returns_201_with_both_memberships(
        client, unique_name, ticket_client, project_a, project_b):
    resp = client.post("/api/client-contacts", json={
        "email": f"multi.{unique_name}@clienteexterno.com",
        "username": f"multi_{unique_name}",
        "project_ids": [project_a["id"], project_b["id"]],
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["client_id"] == ticket_client["id"]
    assert body["provisional_password"]

    listed = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    assert listed.status_code == 200
    contact = next(c for c in listed.get_json()["items"] if c["id"] == body["id"])
    project_ids = {p["id"] for p in contact["projects"]}
    assert project_ids == {project_a["id"], project_b["id"]}


def test_create_with_duplicate_project_id_dedupes(client, unique_name, ticket_client, project_a):
    resp = client.post("/api/client-contacts", json={
        "email": f"dedupe.{unique_name}@clienteexterno.com",
        "username": f"dedupe_{unique_name}",
        "project_ids": [project_a["id"], project_a["id"]],
    })
    assert resp.status_code == 201, resp.get_json()
    listed = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    contact = next(c for c in listed.get_json()["items"] if c["id"] == resp.get_json()["id"])
    assert len(contact["projects"]) == 1


def test_create_with_projects_from_different_clients_returns_400(
        client, unique_name, project_a, project_other_client):
    resp = client.post("/api/client-contacts", json={
        "email": f"mixed.{unique_name}@clienteexterno.com",
        "username": f"mixed_{unique_name}",
        "project_ids": [project_a["id"], project_other_client["id"]],
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"

    listed = client.get(f"/api/client-contacts?email=mixed.{unique_name}")
    assert listed.get_json()["total"] == 0


def test_create_with_inactive_project_returns_409(client, unique_name, project_a):
    deactivated = client.patch(f"/api/projects/{project_a['id']}/deactivate")
    assert deactivated.status_code == 200

    resp = client.post("/api/client-contacts", json={
        "email": f"inactiveproj.{unique_name}@clienteexterno.com",
        "username": f"inactiveproj_{unique_name}",
        "project_ids": [project_a["id"]],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "project_inactive"


def test_create_legacy_client_id_without_projects_still_works(client, unique_name, ticket_client):
    resp = client.post("/api/client-contacts", json={
        "email": f"legacy.{unique_name}@clienteexterno.com",
        "username": f"legacy_{unique_name}",
        "client_id": ticket_client["id"],
    })
    assert resp.status_code == 201, resp.get_json()
    listed = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    contact = next(c for c in listed.get_json()["items"] if c["id"] == resp.get_json()["id"])
    assert contact["projects"] == []


# ── US2: agregar/quitar Proyectos de un Usuario/cliente existente ───────────

@pytest.fixture()
def contact_in_project_a(client, unique_name, project_a):
    resp = client.post("/api/client-contacts", json={
        "email": f"existing.{unique_name}@clienteexterno.com",
        "username": f"existing_{unique_name}",
        "project_ids": [project_a["id"]],
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_add_project_same_client_returns_201_and_appears_in_list(
        client, ticket_client, contact_in_project_a, project_a, project_b):
    resp = client.post(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects",
        json={"project_id": project_b["id"]})
    assert resp.status_code == 201, resp.get_json()

    listed = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    contact = next(c for c in listed.get_json()["items"] if c["id"] == contact_in_project_a["id"])
    project_ids = {p["id"] for p in contact["projects"]}
    assert project_ids == {project_a["id"], project_b["id"]}


def test_add_project_different_client_returns_400(
        client, contact_in_project_a, project_other_client):
    resp = client.post(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects",
        json={"project_id": project_other_client["id"]})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_add_already_assigned_project_returns_409(client, contact_in_project_a, project_a):
    resp = client.post(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects",
        json={"project_id": project_a["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_member"


def test_remove_project_returns_204_and_disappears_from_list(
        client, ticket_client, contact_in_project_a, project_a):
    resp = client.delete(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects/{project_a['id']}")
    assert resp.status_code == 204

    listed = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    contact = next(c for c in listed.get_json()["items"] if c["id"] == contact_in_project_a["id"])
    assert contact["projects"] == []


def test_remove_project_not_a_member_returns_404(client, contact_in_project_a, project_b):
    resp = client.delete(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects/{project_b['id']}")
    assert resp.status_code == 404


def test_remove_project_unknown_contact_returns_404(client, project_a):
    resp = client.delete(f"/api/client-contacts/{uuid.uuid4()}/projects/{project_a['id']}")
    assert resp.status_code == 404


# ── spec 016: corregir el Cliente de un contacto con 0 Proyectos asignados ──

def test_add_different_client_project_when_zero_projects_corrects_client(
        client, ticket_client, other_client, contact_in_project_a, project_a, project_other_client):
    removed = client.delete(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects/{project_a['id']}")
    assert removed.status_code == 204

    resp = client.post(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects",
        json={"project_id": project_other_client["id"]})
    assert resp.status_code == 201, resp.get_json()

    listed_new = client.get(f"/api/client-contacts?client_id={other_client['id']}")
    assert any(c["id"] == contact_in_project_a["id"] for c in listed_new.get_json()["items"])

    listed_old = client.get(f"/api/client-contacts?client_id={ticket_client['id']}")
    assert not any(c["id"] == contact_in_project_a["id"] for c in listed_old.get_json()["items"])


def test_add_different_client_project_with_existing_projects_still_rejected(
        client, contact_in_project_a, project_other_client):
    """Confirma que la corrección de Cliente (spec 016) no afecta la regla estricta de spec 015
    cuando el contacto ya tiene 1+ Proyectos asignados."""
    resp = client.post(
        f"/api/client-contacts/{contact_in_project_a['id']}/projects",
        json={"project_id": project_other_client["id"]})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"
