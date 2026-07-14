"""Bloque `sla` en el detalle del ticket y su evolución por transición (spec 014, Historia 2)."""
import pytest


@pytest.fixture()
def sla_ticket_setup(client, ticket_client, ticket_resource, unique_name):
    project = client.post("/api/projects", json={
        "client_id": ticket_client["id"], "name": f"Proyecto Tkt SLA {unique_name}",
        "start_date": "2026-01-01",
    }).get_json()
    client.post("/api/sla-rules", json={
        "project_id": project["id"], "priority": "high",
        "contact_minutes": 15, "execution_minutes": 480,
    })
    ticket = client.post("/api/tickets", json={
        "title": "Ticket con SLA", "description": "desc",
        "ticket_type": "incident", "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"], "project_id": project["id"],
    }).get_json()
    return {"project": project, "ticket": ticket, "resource": ticket_resource}


def test_new_ticket_starts_sla_phase_contacto_running(sla_ticket_setup):
    sla = sla_ticket_setup["ticket"]["sla"]
    assert sla["phase"] == "contacto"
    assert sla["status"] == "corriendo"
    assert sla["phase_limit_minutes"] == 15
    assert sla["rule_id"] is not None


def test_ticket_without_matching_rule_is_sin_sla(client, ticket_client, unique_name):
    project = client.post("/api/projects", json={
        "client_id": ticket_client["id"], "name": f"Proyecto Sin SLA {unique_name}",
        "start_date": "2026-01-01",
    }).get_json()
    ticket = client.post("/api/tickets", json={
        "title": "Sin regla", "description": "desc", "ticket_type": "incident",
        "priority": "critical", "severity": "s2",
        "client_id": ticket_client["id"], "project_id": project["id"],
    }).get_json()
    assert ticket["sla"]["status"] == "sin_sla"
    assert ticket["sla"]["phase"] is None


def test_assign_resolver_transitions_sla_to_ejecucion_phase(client, sla_ticket_setup):
    ticket_id = sla_ticket_setup["ticket"]["id"]
    resource_id = sla_ticket_setup["resource"]["id"]
    response = client.post(f"/api/tickets/{ticket_id}/assign",
                           json={"assignee_id": resource_id, "mode": "resolver"})
    assert response.status_code == 200, response.get_json()
    sla = response.get_json()["ticket"]["sla"]
    assert sla["phase"] == "ejecucion"
    assert sla["phase_limit_minutes"] == 480
    assert sla["contact_result"] == "cumplido"
    assert sla["consumed_seconds"] == 0


def test_pendiente_usuario_pauses_sla_and_resume_keeps_consumed(client, sla_ticket_setup):
    ticket_id = sla_ticket_setup["ticket"]["id"]
    resource_id = sla_ticket_setup["resource"]["id"]
    client.post(f"/api/tickets/{ticket_id}/assign", json={"assignee_id": resource_id, "mode": "resolver"})
    client.post(f"/api/tickets/{ticket_id}/comments",
               json={"comment_type": "confirmacion_atencion", "body": "Confirmado"})
    response = client.post(f"/api/tickets/{ticket_id}/comments",
                           json={"comment_type": "solicitud_informacion", "body": "Necesito más datos"})
    assert response.status_code == 201, response.get_json()

    detail = client.get(f"/api/tickets/{ticket_id}").get_json()
    assert detail["status"] == "pendiente_usuario"
    assert detail["sla"]["status"] == "pausado"
    consumed_paused = detail["sla"]["consumed_seconds"]

    response = client.post(f"/api/tickets/{ticket_id}/comments",
                           json={"comment_type": "respuesta_usuario", "body": "Aquí está la info"})
    assert response.status_code == 201, response.get_json()
    detail = client.get(f"/api/tickets/{ticket_id}").get_json()
    assert detail["status"] == "en_ejecucion"
    assert detail["sla"]["status"] == "corriendo"
    assert detail["sla"]["consumed_seconds"] >= consumed_paused


def test_cancel_stops_sla(client, sla_ticket_setup):
    ticket_id = sla_ticket_setup["ticket"]["id"]
    response = client.post(f"/api/tickets/{ticket_id}/cancel", json={"body": "Ya no aplica"})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["sla"]["status"] == "detenido"
    assert response.get_json()["sla"]["phase"] == "cerrado"


def test_task_record_type_has_no_sla(client, ticket_client, unique_name):
    """FR-012: las Tareas no tienen SLA aunque compartan tabla/FSM con los Tickets."""
    record_types = client.get("/api/catalogs/record-types").get_json()["items"]
    tarea_type = next(rt for rt in record_types if rt["name"] == "Tarea")
    ticket = client.post("/api/tickets", json={
        "title": "Una tarea", "description": "desc", "ticket_type": "incident",
        "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"], "record_type_id": tarea_type["id"],
    }).get_json()
    assert ticket["sla"]["status"] == "sin_sla"
    assert ticket["sla"]["phase"] is None
