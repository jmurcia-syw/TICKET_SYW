"""spec 009, US2 — PATCH /api/tickets/{id}/status (transición libre + comentario obligatorio),
reemplaza POST /{id}/task-transition (spec 008, retirado)."""
import pytest


@pytest.fixture()
def tarea_record_type_id(client):
    items = client.get("/api/catalogs/record-types?active=all").get_json()["items"]
    tarea = next(i for i in items if i["name"] == "Tarea")
    return tarea["id"]


def _make_task(client, ticket_client, tarea_record_type_id, **overrides):
    payload = {
        "title": "Documentos de diseño", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
        **overrides,
    }
    resp = client.post("/api/tickets", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_status_change_skips_intermediate_states(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    assert created["status"] == "nuevo"

    resp = client.patch(f"/api/tickets/{created['id']}/status",
                        json={"status": "cerrado", "comment": "Se completó directamente"})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["status"] == "cerrado"

    transitions = resp.get_json()["transitions"]
    assert transitions[-1]["from_status"] == "nuevo"
    assert transitions[-1]["to_status"] == "cerrado"


def test_status_change_allows_backwards_transition(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    client.patch(f"/api/tickets/{created['id']}/status",
                json={"status": "cerrado", "comment": "Cierre inicial"})
    resp = client.patch(f"/api/tickets/{created['id']}/status",
                        json={"status": "nuevo", "comment": "Se reabre"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "nuevo"


def test_status_change_requires_comment(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    resp = client.patch(f"/api/tickets/{created['id']}/status", json={"status": "cerrado"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_status_change_rejects_unknown_status(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    resp = client.patch(f"/api/tickets/{created['id']}/status",
                        json={"status": "no_existe", "comment": "x"})
    assert resp.status_code == 400


def test_status_change_allowed_for_resolutor_without_edit_permission(
        client, resolver_auth, ticket_client, tarea_record_type_id):
    """Resolutor tiene `tickets:transition` pero no `tickets:edit` — el endpoint debe usar el
    primero (mismo criterio que /comments, /testing, /cancel), no el segundo (reservado para
    PATCH de campos). Encontrado en validación manual E2E contra Docker real."""
    created = client.post("/api/tickets", json={
        "title": "Tarea del resolutor", "description": "Descripción",
        "client_id": ticket_client["id"], "record_type_id": tarea_record_type_id,
    }, headers=resolver_auth).get_json()

    resp = client.patch(f"/api/tickets/{created['id']}/status",
                        json={"status": "cerrado", "comment": "Listo"}, headers=resolver_auth)
    assert resp.status_code == 200, resp.get_json()


def test_status_change_on_regular_ticket_returns_409_not_a_task(client, make_ticket):
    ticket = make_ticket()
    resp = client.patch(f"/api/tickets/{ticket['id']}/status",
                        json={"status": "cerrado", "comment": "x"})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "not_a_task"


def test_status_change_creates_internal_comment(client, ticket_client, tarea_record_type_id):
    created = _make_task(client, ticket_client, tarea_record_type_id)
    resp = client.patch(f"/api/tickets/{created['id']}/status",
                        json={"status": "en_ejecucion", "comment": "Arrancamos"})
    comments = resp.get_json()["comments"]
    assert any(c["comment_type"] == "comentario_interno" and c["body"] == "Arrancamos"
              for c in comments)


def test_task_shows_all_classification_fields(client, ticket_client, tarea_record_type_id):
    """spec 009 FR-006: Tipo/Severidad/Nivel de escalamiento visibles y editables igual que
    en un Ticket (revierte la spec 008)."""
    created = _make_task(client, ticket_client, tarea_record_type_id,
                         ticket_type="evolutive", severity="s1", escalation_level="n1")
    assert created["ticket_type"] == "evolutive"
    assert created["severity"] == "s1"
    assert created["escalation_level"] == "n1"

    patched = client.patch(f"/api/tickets/{created['id']}",
                           json={"severity": "s2", "escalation_level": "n3"})
    assert patched.status_code == 200
    assert patched.get_json()["severity"] == "s2"
    assert patched.get_json()["escalation_level"] == "n3"
