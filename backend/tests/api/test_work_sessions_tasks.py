"""spec 009, US1 — fix de Registro de tiempo: el creador de una Tarea/Subtarea puede
registrar tiempo aunque no sea su `assignee_id` formal (FR-001/FR-002).

La regresión de Ticket (rechazo si no hay ninguna relación) ya está cubierta por
test_work_sessions_create.py::test_create_rejects_ticket_not_assigned_to_caller — el fix
aquí solo agrega un chequeo adicional cuando el registro es Tarea/Subtarea (`is_task=True`),
sin tocar la ruta de Ticket.
"""
from datetime import date

import pytest


@pytest.fixture()
def tarea_record_type_id(client):
    items = client.get("/api/catalogs/record-types?active=all").get_json()["items"]
    tarea = next(i for i in items if i["name"] == "Tarea")
    return tarea["id"]


def _resolutor_role_id(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    return next(r["id"] for r in roles if r["name"] == "Resolutor")


def _make_resource(client, unique_name, suffix: str) -> dict:
    role_id = _resolutor_role_id(client)
    user_resp = client.post("/api/users", json={
        "email": f"otro.{suffix}.{unique_name}@sywork.net",
        "username": f"otro_{suffix}_{unique_name}",
        "role_id": role_id,
    })
    assert user_resp.status_code == 201, user_resp.get_json()
    user_id = user_resp.get_json()["user"]["id"]
    resource_resp = client.post("/api/resources", json={
        "full_name": f"Recurso {suffix} {unique_name}",
        "email": f"recurso.{suffix}.{unique_name}@sywork.net",
        "user_id": user_id,
    })
    assert resource_resp.status_code == 201, resource_resp.get_json()
    return resource_resp.get_json()


def _create_ws(client, ticket_id, auth, duration_minutes=60):
    return client.post("/api/work-sessions", json={
        "ticket_id": ticket_id, "work_date": date.today().isoformat(),
        "duration_minutes": duration_minutes,
    }, headers=auth)


def test_creator_of_own_task_can_register_time(
        client, resolver_auth, ticket_resource, ticket_client, tarea_record_type_id):
    created = client.post("/api/tickets", json={
        "title": "Tarea propia", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
    }, headers=resolver_auth).get_json()
    assert created["assignee"]["id"] == ticket_resource["id"]

    resp = _create_ws(client, created["id"], auth=resolver_auth)
    assert resp.status_code == 201, resp.get_json()


def test_creator_of_subtask_assigned_to_other_can_register_time(
        client, resolver_auth, ticket_resource, ticket_client, tarea_record_type_id, unique_name):
    tarea = client.post("/api/tickets", json={
        "title": "Tarea padre", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
    }, headers=resolver_auth).get_json()

    other = _make_resource(client, unique_name, "sub")
    subtask = client.post("/api/tickets", json={
        "title": "Subtarea de otro Encargado", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
        "parent_task_id": tarea["id"], "assignee_id": other["id"],
    }, headers=resolver_auth).get_json()
    assert subtask["assignee"]["id"] == other["id"]

    # El creador (resolver) no es el assignee de la subtarea, pero sí su creador.
    resp = _create_ws(client, subtask["id"], auth=resolver_auth)
    assert resp.status_code == 201, resp.get_json()


def test_unrelated_resource_still_rejected(
        client, app, resolver_auth, ticket_client, tarea_record_type_id, unique_name):
    created = client.post("/api/tickets", json={
        "title": "Tarea de otro", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
    }, headers=resolver_auth).get_json()

    stranger = _make_resource(client, unique_name, "stranger")
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(stranger["user_id"]))
    resp = _create_ws(client, created["id"], auth={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "not_assigned"
