import pytest


@pytest.fixture()
def tarea_record_type_id(client):
    items = client.get("/api/catalogs/record-types?active=all").get_json()["items"]
    tarea = next(i for i in items if i["name"] == "Tarea")
    return tarea["id"]


def _make_task(client, ticket_client, tarea_record_type_id, **overrides):
    payload = {
        "title": "Preparar demo para el cliente",
        "description": "Armar el ambiente de demo antes del viernes",
        "client_id": ticket_client["id"],
        "record_type_id": tarea_record_type_id,
        **overrides,
    }
    resp = client.post("/api/tickets", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ── Creación (T008, US1) ─────────────────────────────────────────────────────

def test_create_task_without_incident_classification_fields(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    assert created["record_type_id"] == tarea_record_type_id
    # spec 009: la Tarea nace en "nuevo" como cualquier registro (catálogo unificado, ya no
    # tiene un estado inicial propio "pendiente" de la spec 008).
    assert created["status"] == "nuevo"

    detail = client.get(f"/api/tickets/{created['id']}").get_json()
    assert detail["status"] == "nuevo"
    assert detail["status_label"] == "Nuevo"


def test_create_task_respects_incident_fields_if_sent(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id,
                         ticket_type="evolutive", severity="s1")
    # spec 009 revierte la spec 008: si se envían, se respetan (siguen siendo opcionales).
    assert created["ticket_type"] == "evolutive"
    assert created["severity"] == "s1"


def test_create_task_auto_assigns_creators_own_resource(
        client, resolver_auth, ticket_resource, ticket_client, tarea_record_type_id):
    """Sin esto la Tarea quedaría huérfana y nunca aparecería en "Mis Tareas" del creador
    (create() nunca asigna un ticket por defecto — ver comentario en tickets.py)."""
    resp = client.post("/api/tickets", json={
        "title": "Tarea autoasignada", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
    }, headers=resolver_auth)
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["assignee"]["id"] == ticket_resource["id"]


def test_encargado_cannot_create_a_task(client, encargado_auth, tarea_record_type_id):
    resp = client.post("/api/tickets", json={
        "title": "Intento de tarea desde autoservicio",
        "description": "No debería crearse como Tarea",
        "record_type_id": tarea_record_type_id,
    }, headers=encargado_auth)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["record_type_id"] != tarea_record_type_id
    assert body["status"] == "nuevo"


# Ciclo de vida de la Tarea (transición libre + comentario obligatorio) — ver
# backend/tests/api/test_tickets_status_transition.py (spec 009).
# Lista real (list_id) — ver backend/tests/api/test_task_lists.py (spec 009).

# ── Registro relacionado (T020/T022, US2) ────────────────────────────────────

def test_create_task_with_related_ticket_of_same_client(client, ticket_client, tarea_record_type_id, make_ticket):
    related = make_ticket()
    created = _make_task(client, ticket_client, tarea_record_type_id, related_ticket_id=related["id"])
    assert created["related_ticket_id"] == related["id"]

    related_detail = client.get(f"/api/tickets/{related['id']}").get_json()
    assert len(related_detail["related_from"]) == 1
    assert related_detail["related_from"][0]["id"] == created["id"]
    assert related_detail["related_from"][0]["record_type"] == "Tarea"


def test_create_task_related_ticket_of_other_client_returns_409(client, unique_name, ticket_client, tarea_record_type_id):
    other_client = client.post("/api/clients", json={"name": f"Otro Cliente {unique_name}"}).get_json()
    other_ticket = client.post("/api/tickets", json={
        "title": "Ticket de otro cliente", "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": other_client["id"],
    }).get_json()
    resp = client.post("/api/tickets", json={
        "title": "Tarea con vinculo cruzado", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
        "related_ticket_id": other_ticket["id"],
    })
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "related_ticket_mismatch"


def test_patch_ticket_related_ticket_of_other_client_returns_409(client, unique_name, ticket_client, make_ticket):
    """El fix de FR-005 aplica también a un Ticket normal, no solo a Tareas."""
    other_client = client.post("/api/clients", json={"name": f"Otro Cliente Patch {unique_name}"}).get_json()
    other_ticket = client.post("/api/tickets", json={
        "title": "Ticket de otro cliente", "description": "Descripción",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": other_client["id"],
    }).get_json()
    ticket = make_ticket()
    resp = client.patch(f"/api/tickets/{ticket['id']}", json={"related_ticket_id": other_ticket["id"]})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "related_ticket_mismatch"


def test_patch_related_ticket_self_reference_rejected(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    resp = client.patch(f"/api/tickets/{created['id']}", json={"related_ticket_id": created["id"]})
    assert resp.status_code == 400
