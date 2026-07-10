"""Skills Requeridas en el Ticket (spec 011) — Escenarios 1-6 del quickstart."""
import pytest


def _make_skill(client, unique_name, suffix=""):
    resp = client.post("/api/skills", json={
        "code": f"TSK_{unique_name}{suffix}", "label": f"Test Skill {suffix}", "skill_type": "tecnico",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture()
def two_skills(client, unique_name):
    return [_make_skill(client, unique_name, "_A"), _make_skill(client, unique_name, "_B")]


# ── US1 — asignar Skills requeridas (Escenario 1) ───────────────────────────────

def test_assign_skills_to_ticket_without_any(client, make_ticket, two_skills):
    ticket = make_ticket()
    assert ticket["skills"] == []

    skill_ids = [s["id"] for s in two_skills]
    response = client.patch(f"/api/tickets/{ticket['id']}/skills", json={"skill_ids": skill_ids})
    assert response.status_code == 200, response.get_json()
    returned_ids = {s["id"] for s in response.get_json()["skills"]}
    assert returned_ids == set(skill_ids)

    detail = client.get(f"/api/tickets/{ticket['id']}")
    assert {s["id"] for s in detail.get_json()["skills"]} == set(skill_ids)


def test_update_skills_is_full_replacement(client, make_ticket, two_skills, unique_name):
    ticket = make_ticket()
    skill_a, skill_b = two_skills
    client.patch(f"/api/tickets/{ticket['id']}/skills", json={"skill_ids": [skill_a["id"], skill_b["id"]]})

    skill_c = _make_skill(client, unique_name, "_C")
    response = client.patch(f"/api/tickets/{ticket['id']}/skills", json={"skill_ids": [skill_c["id"]]})
    assert response.status_code == 200, response.get_json()
    assert [s["id"] for s in response.get_json()["skills"]] == [skill_c["id"]]


def test_update_skills_ignores_duplicate_ids(client, make_ticket, two_skills):
    ticket = make_ticket()
    skill_a = two_skills[0]
    response = client.patch(f"/api/tickets/{ticket['id']}/skills",
                            json={"skill_ids": [skill_a["id"], skill_a["id"]]})
    assert response.status_code == 200, response.get_json()
    assert [s["id"] for s in response.get_json()["skills"]] == [skill_a["id"]]


def test_resolver_cannot_edit_ticket_skills(client, make_ticket, two_skills, resolver_auth):
    """Resolutor tiene tickets:view/create/transition pero NO tickets:edit en este sistema
    (research.md Decisión 4) — igual que para el resto de la clasificación del ticket."""
    ticket = make_ticket()
    response = client.patch(f"/api/tickets/{ticket['id']}/skills",
                            json={"skill_ids": [two_skills[0]["id"]]}, headers=resolver_auth)
    assert response.status_code == 403, response.get_json()


def test_update_skills_ticket_not_found(client, two_skills):
    import uuid
    response = client.patch(f"/api/tickets/{uuid.uuid4()}/skills", json={"skill_ids": [two_skills[0]["id"]]})
    assert response.status_code == 404, response.get_json()


# ── US2 — cambiar Skills en cualquier estado (Escenario 2) ──────────────────────

def test_update_skills_allowed_on_cancelled_ticket(client, make_ticket, two_skills):
    ticket = make_ticket()
    cancelled = client.post(f"/api/tickets/{ticket['id']}/cancel", json={"body": "Ya no aplica"})
    assert cancelled.status_code == 200, cancelled.get_json()
    assert cancelled.get_json()["status"] == "cancelado"

    response = client.patch(f"/api/tickets/{ticket['id']}/skills",
                            json={"skill_ids": [s["id"] for s in two_skills]})
    assert response.status_code == 200, response.get_json()
    assert len(response.get_json()["skills"]) == 2
    assert response.get_json()["status"] == "cancelado"


def test_update_skills_does_not_change_status_or_create_comment(client, make_ticket, two_skills):
    ticket = make_ticket()
    before_comments = client.get(f"/api/tickets/{ticket['id']}").get_json()["comments"]

    response = client.patch(f"/api/tickets/{ticket['id']}/skills",
                            json={"skill_ids": [two_skills[0]["id"]]})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["status"] == "nuevo"
    after_comments = response.get_json()["comments"]
    assert len(after_comments) == len(before_comments)


# ── US3 — visualizar Skills requeridas (Escenario 4) ─────────────────────────────

def test_view_only_resolver_sees_ticket_skills(client, make_ticket, ticket_resource, two_skills, resolver_auth):
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/assign", json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    client.patch(f"/api/tickets/{ticket['id']}/skills", json={"skill_ids": [s["id"] for s in two_skills]})

    response = client.get(f"/api/tickets/{ticket['id']}", headers=resolver_auth)
    assert response.status_code == 200, response.get_json()
    assert {s["id"] for s in response.get_json()["skills"]} == {s["id"] for s in two_skills}


def test_ticket_without_skills_shows_empty_list(client, make_ticket):
    ticket = make_ticket()
    response = client.get(f"/api/tickets/{ticket['id']}")
    assert response.get_json()["skills"] == []


# ── Edge case FR-007 — eliminar una Skill en uso (Escenario 5) ──────────────────

def test_delete_skill_assigned_to_ticket_is_blocked(client, make_ticket, unique_name):
    skill = _make_skill(client, unique_name, "_INUSE")
    ticket = make_ticket()
    client.patch(f"/api/tickets/{ticket['id']}/skills", json={"skill_ids": [skill["id"]]})

    response = client.delete(f"/api/skills/{skill['id']}")
    assert response.status_code == 409, response.get_json()
    assert response.get_json()["error"] == "skill_in_use"

    # El ticket conserva la referencia sin cambios
    detail = client.get(f"/api/tickets/{ticket['id']}")
    assert [s["id"] for s in detail.get_json()["skills"]] == [skill["id"]]


def test_delete_skill_not_in_use_succeeds(client, unique_name):
    skill = _make_skill(client, unique_name, "_UNUSED")
    response = client.delete(f"/api/skills/{skill['id']}")
    assert response.status_code == 204
