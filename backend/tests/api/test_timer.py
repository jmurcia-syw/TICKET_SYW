"""Cronómetro manual de tiempo (spec 012, provisional) — Escenarios 1-6 del quickstart."""
from datetime import datetime, timedelta, timezone
import uuid

import pytest


def _assign(client, ticket_id, resource_id):
    return client.post(f"/api/tickets/{ticket_id}/assign",
                       json={"assignee_id": resource_id, "mode": "resolver"})


def _rewind_started_at(resource_id: str, minutes: int) -> None:
    """Retrocede `started_at` del cronómetro del recurso para simular tiempo transcurrido
    (US2/T016) sin depender de `time.sleep` en los tests."""
    from backend.infra.database import get_db
    from backend.infra.repositories.ticket_timer_repo import TicketTimerRepository
    db = get_db()
    repo = TicketTimerRepository(db)
    timer = repo.get_by_resource(uuid.UUID(resource_id))
    timer.started_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    repo.save(timer)


@pytest.fixture()
def second_resolver_user(db_session, unique_name):
    """Segundo usuario Resolutor, independiente de `resolver_user` — para probar el
    aislamiento entre recursos (US3)."""
    from backend.domain.entities.user import User
    from backend.infra.repositories.role_repo import RoleRepository
    from backend.infra.repositories.user_repo import UserRepository
    resolutor_role = RoleRepository(db_session).get_by_name("Resolutor")
    user = User(
        id=uuid.uuid4(), email=f"test2.{unique_name}@sywork.net", username=f"test2_{unique_name}",
        role=resolutor_role, active=True,
    )
    return UserRepository(db_session).create(user)


@pytest.fixture()
def second_resolver_auth(app, second_resolver_user):
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(second_resolver_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_ticket_resource(client, unique_name, second_resolver_user):
    response = client.post("/api/resources", json={
        "full_name": f"Resolutor Timer B {unique_name}",
        "email": f"resolutor.timerb.{unique_name}@sywork.net",
        "user_id": str(second_resolver_user.id),
    })
    assert response.status_code == 201, response.get_json()
    return response.get_json()


# ── US1 — ciclo iniciar/pausar/reanudar/terminar (Escenario 1, 4, 6 del quickstart) ────────

def test_get_current_inactive_by_default(client, ticket_resource, resolver_auth):
    response = client.get("/api/timer", headers=resolver_auth)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["status"] == "inactive"


def test_start_pause_resume_finish_cycle(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])

    started = client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)
    assert started.status_code == 201, started.get_json()
    assert started.get_json()["status"] == "running"
    assert started.get_json()["ticket_id"] == ticket["id"]

    _rewind_started_at(ticket_resource["id"], minutes=5)

    paused = client.post("/api/timer/pause", headers=resolver_auth)
    assert paused.status_code == 200, paused.get_json()
    assert paused.get_json()["status"] == "paused"
    assert paused.get_json()["total_seconds"] >= 300

    # Pausado no avanza entre llamadas.
    still_paused = client.get("/api/timer", headers=resolver_auth)
    assert still_paused.get_json()["total_seconds"] == paused.get_json()["total_seconds"]

    resumed = client.post("/api/timer/resume", headers=resolver_auth)
    assert resumed.status_code == 200
    assert resumed.get_json()["status"] == "running"

    finished = client.post("/api/timer/finish", json={"note": "cronómetro"}, headers=resolver_auth)
    assert finished.status_code == 201, finished.get_json()
    assert finished.get_json()["ticket_id"] == ticket["id"]
    assert finished.get_json()["duration_minutes"] >= 5

    back_to_inactive = client.get("/api/timer", headers=resolver_auth)
    assert back_to_inactive.get_json()["status"] == "inactive"

    listing = client.get("/api/work-sessions", headers=resolver_auth)
    assert any(item["ticket_id"] == ticket["id"] for item in listing.get_json()["items"])


def test_start_rejects_second_ticket_while_active(client, make_ticket, ticket_resource, resolver_auth):
    ticket_a = make_ticket()
    ticket_b = make_ticket()
    _assign(client, ticket_a["id"], ticket_resource["id"])
    _assign(client, ticket_b["id"], ticket_resource["id"])

    first = client.post("/api/timer/start", json={"ticket_id": ticket_a["id"]}, headers=resolver_auth)
    assert first.status_code == 201

    second = client.post("/api/timer/start", json={"ticket_id": ticket_b["id"]}, headers=resolver_auth)
    assert second.status_code == 409
    assert second.get_json()["error"] == "timer_already_active"
    assert second.get_json()["ticket_id"] == ticket_a["id"]


def test_start_rejects_not_assigned_ticket(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()  # sin asignar a ticket_resource
    response = client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)
    assert response.status_code == 403
    assert response.get_json()["error"] == "not_assigned"


def test_finish_rejects_duration_too_short(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)

    response = client.post("/api/timer/finish", headers=resolver_auth)
    assert response.status_code == 409
    assert response.get_json()["error"] == "duration_too_short"

    # El cronómetro no se resetea — sigue activo para reintentar (FR-007).
    still_active = client.get("/api/timer", headers=resolver_auth)
    assert still_active.get_json()["status"] == "running"


def test_finish_blocks_on_closed_ticket(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)
    _rewind_started_at(ticket_resource["id"], minutes=5)

    from backend.infra.database import get_db
    from backend.infra.repositories.ticket_repo import TicketRepository
    TicketRepository(get_db()).update_fields(ticket["id"], status="cerrado")

    response = client.post("/api/timer/finish", headers=resolver_auth)
    assert response.status_code == 409
    assert response.get_json()["error"] == "ticket_closed"

    # El cronómetro tampoco se resetea en este caso (clarificación 2026-07-09, FR-008).
    still_active = client.get("/api/timer", headers=resolver_auth)
    assert still_active.get_json()["status"] == "running"
    assert still_active.get_json()["total_seconds"] >= 300


def test_timer_requires_authentication(anon_client):
    response = anon_client.get("/api/timer")
    assert response.status_code == 401


# ── US2 — persistencia entre recargas/sesiones (Escenario 2 del quickstart) ────────────────

def test_running_timer_survives_reload_and_new_session(client, make_ticket, ticket_resource,
                                                        resolver_auth, app, resolver_user):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)
    _rewind_started_at(ticket_resource["id"], minutes=10)

    # Simula una "recarga" con una request nueva y, además, una sesión JWT nueva (cierre/reapertura
    # de sesión) — ambas deben reflejar el mismo tiempo derivado de `started_at` en BD.
    from flask_jwt_extended import create_access_token
    with app.app_context():
        new_session_token = create_access_token(identity=str(resolver_user.id))
    new_session_auth = {"Authorization": f"Bearer {new_session_token}"}

    reloaded = client.get("/api/timer", headers=resolver_auth)
    new_session = client.get("/api/timer", headers=new_session_auth)
    assert reloaded.get_json()["status"] == "running"
    assert reloaded.get_json()["total_seconds"] >= 600
    assert new_session.get_json()["total_seconds"] >= 600


def test_paused_timer_stays_constant_across_calls(client, make_ticket, ticket_resource, resolver_auth):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)
    _rewind_started_at(ticket_resource["id"], minutes=3)
    client.post("/api/timer/pause", headers=resolver_auth)

    first = client.get("/api/timer", headers=resolver_auth)
    second = client.get("/api/timer", headers=resolver_auth)
    assert first.get_json()["total_seconds"] == second.get_json()["total_seconds"]


# ── US3 — cronómetro personal por recurso (Escenario 3 del quickstart) ─────────────────────

def test_other_resource_does_not_see_active_timer(client, make_ticket, ticket_resource,
                                                   resolver_auth, second_resolver_auth,
                                                   second_ticket_resource):
    ticket = make_ticket()
    _assign(client, ticket["id"], ticket_resource["id"])
    started = client.post("/api/timer/start", json={"ticket_id": ticket["id"]}, headers=resolver_auth)
    assert started.status_code == 201, started.get_json()

    other_view = client.get("/api/timer", headers=second_resolver_auth)
    assert other_view.status_code == 200, other_view.get_json()
    assert other_view.get_json()["status"] == "inactive"


def test_two_resources_run_independent_timers(client, make_ticket, ticket_resource,
                                              resolver_auth, second_resolver_auth,
                                              second_ticket_resource):
    # Cada recurso en su propio ticket: la asignación de resolutor (Triage) transiciona el
    # ticket de NUEVO a CONTACTO y no admite un segundo "assign" sobre el mismo ticket — probar
    # el aislamiento del cronómetro (FR-005) no depende de que compartan el mismo ticket.
    ticket_a = make_ticket()
    ticket_b = make_ticket()
    assign_a = _assign(client, ticket_a["id"], ticket_resource["id"])
    assign_b = _assign(client, ticket_b["id"], second_ticket_resource["id"])
    assert assign_a.status_code == 200, assign_a.get_json()
    assert assign_b.status_code == 200, assign_b.get_json()

    started_a = client.post("/api/timer/start", json={"ticket_id": ticket_a["id"]}, headers=resolver_auth)
    started_b = client.post("/api/timer/start", json={"ticket_id": ticket_b["id"]}, headers=second_resolver_auth)
    assert started_a.status_code == 201, started_a.get_json()
    assert started_b.status_code == 201, started_b.get_json()

    _rewind_started_at(ticket_resource["id"], minutes=5)
    client.post("/api/timer/pause", headers=resolver_auth)

    # Pausar el de A no afecta el de B, que sigue corriendo.
    b_state = client.get("/api/timer", headers=second_resolver_auth)
    assert b_state.get_json()["status"] == "running"

    _rewind_started_at(second_ticket_resource["id"], minutes=2)
    finished_a = client.post("/api/timer/resume", headers=resolver_auth)
    assert finished_a.status_code == 200
    finished_a = client.post("/api/timer/finish", headers=resolver_auth)
    finished_b = client.post("/api/timer/finish", headers=second_resolver_auth)
    assert finished_a.status_code == 201
    assert finished_b.status_code == 201
    assert finished_a.get_json()["id"] != finished_b.get_json()["id"]
