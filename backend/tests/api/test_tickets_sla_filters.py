"""Filtros `sla_status` y `sla_expiring_within_hours` en `GET /api/tickets` (spec 014, Historia 3)."""
from datetime import date, datetime, timedelta, timezone

import pytest

# OBS-0011: la fecha de inicio de un proyecto no puede quedar en un mes anterior al actual.
_PROJECT_START = date.today().strftime("%Y-%m-01")


@pytest.fixture()
def sla_filter_setup(client, ticket_client, unique_name, db_session):
    project = client.post("/api/projects", json={
        "client_id": ticket_client["id"], "name": f"Proyecto Filtros SLA {unique_name}",
        "start_date": _PROJECT_START,
    }).get_json()
    client.post("/api/sla-rules", json={
        "project_id": project["id"], "priority": "high",
        "contact_minutes": 15, "execution_minutes": 480,
    })
    ticket = client.post("/api/tickets", json={
        "title": "Ticket filtros SLA", "description": "desc", "ticket_type": "incident",
        "priority": "high", "severity": "s2",
        "client_id": ticket_client["id"], "project_id": project["id"],
    }).get_json()
    return {"project": project, "ticket": ticket}


def _backdate_last_resume(db_session, ticket_id: str, minutes_ago: int) -> None:
    from backend.infra.models.ticket_model import TicketModel
    import uuid
    model = db_session.get(TicketModel, uuid.UUID(ticket_id))
    model.sla_last_resume_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    db_session.commit()


def test_filter_by_sla_status_corriendo(client, sla_filter_setup):
    ticket_id = sla_filter_setup["ticket"]["id"]
    response = client.get("/api/tickets?sla_status=corriendo&page_size=100")
    assert response.status_code == 200, response.get_json()
    ids = {item["id"] for item in response.get_json()["items"]}
    assert ticket_id in ids


def test_filter_by_sla_status_excludes_other_statuses(client, sla_filter_setup):
    response = client.get("/api/tickets?sla_status=vencido&page_size=100")
    assert response.status_code == 200
    ids = {item["id"] for item in response.get_json()["items"]}
    assert sla_filter_setup["ticket"]["id"] not in ids


def test_filter_expiring_within_hours_includes_near_deadline_ticket(client, sla_filter_setup, db_session):
    ticket_id = sla_filter_setup["ticket"]["id"]
    # Contacto = 15 min límite; consumido "real" simulado en 10 min -> restan 5 min (< 1h).
    _backdate_last_resume(db_session, ticket_id, minutes_ago=10)
    response = client.get("/api/tickets?sla_expiring_within_hours=1&page_size=100")
    assert response.status_code == 200, response.get_json()
    ids = {item["id"] for item in response.get_json()["items"]}
    assert ticket_id in ids


def test_filter_expiring_within_hours_excludes_far_deadline_ticket(client, sla_filter_setup):
    ticket_id = sla_filter_setup["ticket"]["id"]
    # Ticket recién creado: 15 min límite, ~0 consumido -> no cae en "vence en <= 0 horas".
    response = client.get("/api/tickets?sla_expiring_within_hours=0&page_size=100")
    assert response.status_code == 200
    ids = {item["id"] for item in response.get_json()["items"]}
    assert ticket_id not in ids


def test_listing_includes_summarized_sla_block(client, sla_filter_setup):
    ticket_id = sla_filter_setup["ticket"]["id"]
    response = client.get(f"/api/tickets?search={sla_filter_setup['ticket']['ticket_number']}")
    item = next(i for i in response.get_json()["items"] if i["id"] == ticket_id)
    assert item["sla"]["phase"] == "contacto"
    assert item["sla"]["status"] == "corriendo"
