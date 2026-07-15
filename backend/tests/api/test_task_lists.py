"""spec 009, US3 — Listas de tareas administrables dentro de un Proyecto."""
from datetime import date

import pytest

# OBS-0011: la fecha de inicio de un proyecto no puede quedar en un mes anterior al actual.
_PROJECT_START = date.today().strftime("%Y-%m-01")


@pytest.fixture()
def ticket_project(client, ticket_client, unique_name):
    resp = client.post("/api/projects", json={
        "client_id": ticket_client["id"], "name": f"Proyecto {unique_name}",
        "start_date": _PROJECT_START,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture()
def tarea_record_type_id(client):
    items = client.get("/api/catalogs/record-types?active=all").get_json()["items"]
    tarea = next(i for i in items if i["name"] == "Tarea")
    return tarea["id"]


def test_create_and_list_task_list(client, ticket_project):
    resp = client.post(f"/api/projects/{ticket_project['id']}/task-lists", json={"name": "F1: Definiciones"})
    assert resp.status_code == 201, resp.get_json()
    created = resp.get_json()
    assert created["name"] == "F1: Definiciones"
    assert created["task_count"] == 0

    listing = client.get(f"/api/projects/{ticket_project['id']}/task-lists")
    assert listing.status_code == 200
    names = [i["name"] for i in listing.get_json()["items"]]
    assert "F1: Definiciones" in names


def test_create_task_list_requires_name(client, ticket_project):
    resp = client.post(f"/api/projects/{ticket_project['id']}/task-lists", json={"name": "  "})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_task_list_unknown_project_returns_404(client, unique_name):
    resp = client.post("/api/projects/00000000-0000-0000-0000-000000000099/task-lists",
                       json={"name": "x"})
    assert resp.status_code == 404


def test_task_count_reflects_tasks_in_list(
        client, ticket_client, ticket_project, tarea_record_type_id):
    task_list = client.post(f"/api/projects/{ticket_project['id']}/task-lists",
                            json={"name": "Esta semana"}).get_json()
    client.post("/api/tickets", json={
        "title": "Tarea 1", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "list_id": task_list["id"],
    })
    client.post("/api/tickets", json={
        "title": "Tarea 2", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "list_id": task_list["id"],
    })
    listing = client.get(f"/api/projects/{ticket_project['id']}/task-lists").get_json()
    found = next(i for i in listing["items"] if i["id"] == task_list["id"])
    assert found["task_count"] == 2


def test_create_task_with_list_of_other_project_returns_409(
        client, ticket_client, ticket_project, tarea_record_type_id, unique_name):
    other_project = client.post("/api/projects", json={
        "client_id": ticket_client["id"], "name": f"Otro proyecto {unique_name}",
        "start_date": _PROJECT_START,
    }).get_json()
    other_list = client.post(f"/api/projects/{other_project['id']}/task-lists",
                             json={"name": "Lista ajena"}).get_json()
    resp = client.post("/api/tickets", json={
        "title": "Tarea con lista cruzada", "description": "d",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
        "record_type_id": tarea_record_type_id, "list_id": other_list["id"],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "list_mismatch"


def test_create_duplicate_list_name_in_same_project_rejected(client, ticket_project):
    """OBS-0010: no se permiten dos Listas con el mismo nombre dentro de un mismo Proyecto."""
    client.post(f"/api/projects/{ticket_project['id']}/task-lists", json={"name": "Sprint 1"})
    dup = client.post(f"/api/projects/{ticket_project['id']}/task-lists", json={"name": "Sprint 1"})
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "name_duplicate"


def test_create_list_name_too_long_rejected(client, ticket_project):
    """OBS-0010: nombre de Lista de más de 60 caracteres es rechazado."""
    resp = client.post(f"/api/projects/{ticket_project['id']}/task-lists", json={"name": "A" * 61})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_rename_task_list(client, ticket_project):
    task_list = client.post(f"/api/projects/{ticket_project['id']}/task-lists",
                            json={"name": "Original"}).get_json()
    resp = client.patch(f"/api/task-lists/{task_list['id']}", json={"name": "Renombrada"})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Renombrada"


def test_patch_unknown_task_list_returns_404(client):
    resp = client.patch("/api/task-lists/00000000-0000-0000-0000-000000000099",
                        json={"name": "x"})
    assert resp.status_code == 404
