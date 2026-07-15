"""spec 009, US4/US5 — Subtareas (Nivel 5) con Encargado y estado propios, y comentarios
simples aislados por registro."""
from datetime import date

import pytest

# OBS-0011: la fecha de inicio de un proyecto no puede quedar en un mes anterior al actual.
_PROJECT_START = date.today().strftime("%Y-%m-01")


@pytest.fixture()
def tarea_record_type_id(client):
    items = client.get("/api/catalogs/record-types?active=all").get_json()["items"]
    tarea = next(i for i in items if i["name"] == "Tarea")
    return tarea["id"]


@pytest.fixture()
def ticket_project(client, ticket_client, unique_name):
    resp = client.post("/api/projects", json={
        "client_id": ticket_client["id"], "name": f"Proyecto {unique_name}",
        "start_date": _PROJECT_START,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _resolutor_role_id(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    return next(r["id"] for r in roles if r["name"] == "Resolutor")


def _make_resource(client, unique_name, suffix: str) -> dict:
    role_id = _resolutor_role_id(client)
    user_resp = client.post("/api/users", json={
        "email": f"sub.{suffix}.{unique_name}@sywork.net",
        "username": f"sub_{suffix}_{unique_name}",
        "role_id": role_id,
    })
    assert user_resp.status_code == 201, user_resp.get_json()
    resource_resp = client.post("/api/resources", json={
        "full_name": f"Recurso Subtarea {suffix} {unique_name}",
        "email": f"recurso.sub.{suffix}.{unique_name}@sywork.net",
        "user_id": user_resp.get_json()["user"]["id"],
    })
    assert resource_resp.status_code == 201, resource_resp.get_json()
    return resource_resp.get_json()


def _make_task(client, ticket_client, ticket_project, tarea_record_type_id, **overrides):
    payload = {
        "title": "Documentos de diseño Activos y Proyecto", "description": "Descripción",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
        "record_type_id": tarea_record_type_id, **overrides,
    }
    resp = client.post("/api/tickets", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_create_subtask_with_own_assignee(
        client, ticket_client, ticket_project, tarea_record_type_id, unique_name):
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id)
    other = _make_resource(client, unique_name, "own")

    subtask = client.post("/api/tickets", json={
        "title": "Revisar módulos de Activos Fijos", "description": "Descripción",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
        "record_type_id": tarea_record_type_id,
        "parent_task_id": tarea["id"], "assignee_id": other["id"],
    })
    assert subtask.status_code == 201, subtask.get_json()
    body = subtask.get_json()
    assert body["parent_task_id"] == tarea["id"]
    assert body["assignee"]["id"] == other["id"]


def test_parent_task_shows_subtasks(
        client, ticket_client, ticket_project, tarea_record_type_id):
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id)
    client.post("/api/tickets", json={
        "title": "Subtarea 1", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": tarea["id"],
    })
    detail = client.get(f"/api/tickets/{tarea['id']}").get_json()
    assert len(detail["subtasks"]) == 1
    assert detail["subtasks"][0]["title"] == "Subtarea 1"


def test_nested_subtask_rejected(
        client, ticket_client, ticket_project, tarea_record_type_id):
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id)
    subtask = client.post("/api/tickets", json={
        "title": "Subtarea", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": tarea["id"],
    }).get_json()

    nested = client.post("/api/tickets", json={
        "title": "Subtarea anidada", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": subtask["id"],
    })
    assert nested.status_code == 409
    assert nested.get_json()["error"] == "nested_subtask_not_allowed"


def test_subtask_parent_must_be_a_task_not_a_ticket(client, make_ticket, tarea_record_type_id):
    ticket = make_ticket()
    resp = client.post("/api/tickets", json={
        "title": "Subtarea de un Ticket", "description": "d",
        "client_id": ticket["client"]["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": ticket["id"],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "parent_task_mismatch"


def test_subtask_inherits_parent_list(
        client, ticket_client, ticket_project, tarea_record_type_id):
    task_list = client.post(f"/api/projects/{ticket_project['id']}/task-lists",
                            json={"name": "F1"}).get_json()
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id,
                       list_id=task_list["id"])
    subtask = client.post("/api/tickets", json={
        "title": "Subtarea con lista heredada", "description": "d",
        "client_id": ticket_client["id"], "project_id": ticket_project["id"],
        "record_type_id": tarea_record_type_id, "parent_task_id": tarea["id"],
    }).get_json()
    assert subtask["list_id"] == task_list["id"]


def test_changing_subtask_status_does_not_affect_parent(
        client, ticket_client, ticket_project, tarea_record_type_id, unique_name):
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id)
    assignee = _make_resource(client, unique_name, "parent-check")
    subtask = client.post("/api/tickets", json={
        "title": "Subtarea", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": tarea["id"], "assignee_id": assignee["id"],
    }).get_json()
    # OBS-0026: cerrar (transición a 'cerrado') ahora exige tiempo registrado.
    ws = client.post("/api/work-sessions", json={
        "ticket_id": subtask["id"], "resource_id": assignee["id"],
        "work_date": date.today().isoformat(), "duration_minutes": 30,
    })
    assert ws.status_code == 201, ws.get_json()

    client.patch(f"/api/tickets/{subtask['id']}/status",
                json={"status": "cerrado", "comment": "Listo"})
    parent_detail = client.get(f"/api/tickets/{tarea['id']}").get_json()
    assert parent_detail["status"] == "nuevo"


def test_simple_comment_on_task_has_no_transition(
        client, ticket_client, ticket_project, tarea_record_type_id):
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id)
    resp = client.post(f"/api/tickets/{tarea['id']}/comments",
                       json={"comment_type": "comentario_interno", "body": "Nota simple"})
    assert resp.status_code == 201, resp.get_json()

    detail = client.get(f"/api/tickets/{tarea['id']}").get_json()
    assert len(detail["transitions"]) == 0
    assert any(c["body"] == "Nota simple" for c in detail["comments"])


def test_comment_on_subtask_isolated_from_parent(
        client, ticket_client, ticket_project, tarea_record_type_id):
    tarea = _make_task(client, ticket_client, ticket_project, tarea_record_type_id)
    subtask = client.post("/api/tickets", json={
        "title": "Subtarea", "description": "d", "client_id": ticket_client["id"],
        "project_id": ticket_project["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": tarea["id"],
    }).get_json()

    client.post(f"/api/tickets/{subtask['id']}/comments",
               json={"comment_type": "comentario_interno", "body": "Comentario de la subtarea"})

    parent_detail = client.get(f"/api/tickets/{tarea['id']}").get_json()
    subtask_detail = client.get(f"/api/tickets/{subtask['id']}").get_json()
    assert not any(c["body"] == "Comentario de la subtarea" for c in parent_detail["comments"])
    assert any(c["body"] == "Comentario de la subtarea" for c in subtask_detail["comments"])
