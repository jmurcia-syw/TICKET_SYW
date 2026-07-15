"""Reglas de SLA por Proyecto y Prioridad (spec 014, Historia 1) — quickstart Validación 1."""
import pytest


@pytest.fixture()
def sla_project(client, ticket_client, unique_name):
    response = client.post("/api/projects", json={
        "client_id": ticket_client["id"],
        "name": f"Proyecto SLA {unique_name}",
        "start_date": "2026-01-01",
    })
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_sla_rule(client, sla_project):
    response = client.post("/api/sla-rules", json={
        "project_id": sla_project["id"], "priority": "high",
        "contact_minutes": 15, "execution_minutes": 480,
    })
    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["project_id"] == sla_project["id"]
    assert body["priority"] == "high"
    assert body["contact_minutes"] == 15
    assert body["execution_minutes"] == 480
    assert body["active"] is True


def test_list_sla_rules_filters_by_project(client, sla_project):
    client.post("/api/sla-rules", json={
        "project_id": sla_project["id"], "priority": "critical",
        "contact_minutes": 15, "execution_minutes": 60,
    })
    response = client.get(f"/api/sla-rules?project_id={sla_project['id']}")
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["total"] >= 1
    assert all(item["project_id"] == sla_project["id"] for item in body["items"])


def test_edit_sla_rule_times(client, sla_project):
    created = client.post("/api/sla-rules", json={
        "project_id": sla_project["id"], "priority": "medium",
        "contact_minutes": 15, "execution_minutes": 2880,
    }).get_json()
    response = client.patch(f"/api/sla-rules/{created['id']}", json={"execution_minutes": 4000})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["execution_minutes"] == 4000


def test_deactivate_sla_rule(client, sla_project):
    created = client.post("/api/sla-rules", json={
        "project_id": sla_project["id"], "priority": "low",
        "contact_minutes": 15, "execution_minutes": 7200,
    }).get_json()
    response = client.patch(f"/api/sla-rules/{created['id']}", json={"active": False})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["active"] is False


def test_reject_duplicate_rule_same_project_and_priority(client, sla_project):
    payload = {"project_id": sla_project["id"], "priority": "high",
               "contact_minutes": 15, "execution_minutes": 480}
    client.post("/api/sla-rules", json=payload)
    response = client.post("/api/sla-rules", json=payload)
    assert response.status_code == 409, response.get_json()
    assert response.get_json()["error"] == "duplicate_rule"


def test_reject_missing_project_id(client):
    response = client.post("/api/sla-rules", json={
        "priority": "high", "contact_minutes": 15, "execution_minutes": 480,
    })
    assert response.status_code == 400, response.get_json()


def test_reject_zero_or_negative_minutes(client, sla_project):
    response = client.post("/api/sla-rules", json={
        "project_id": sla_project["id"], "priority": "critical",
        "contact_minutes": 0, "execution_minutes": 60,
    })
    assert response.status_code == 400, response.get_json()


def test_resolver_cannot_manage_sla_rules(client, sla_project, resolver_auth):
    response = client.post("/api/sla-rules", json={
        "project_id": sla_project["id"], "priority": "high",
        "contact_minutes": 15, "execution_minutes": 480,
    }, headers=resolver_auth)
    assert response.status_code == 403, response.get_json()
