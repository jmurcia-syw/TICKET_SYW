def _make_resource(client, unique_name, skill_ids=None):
    payload = {"full_name": f"Resource {unique_name}", "email": f"res.{unique_name}@sywork.net"}
    if skill_ids:
        payload["skill_ids"] = skill_ids
    return client.post("/api/resources", json=payload).get_json()


def test_create_resource_returns_201_with_location(client, unique_name):
    resp = client.post("/api/resources", json={
        "full_name": f"Resource {unique_name}", "email": f"res.{unique_name}@sywork.net",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/resources/{body['id']}"
    assert body["active"] is True


def test_generic_patch_ignores_active_field(client, unique_name):
    """Regression: PATCH /resources/{id} used to allow toggling `active` directly,
    bypassing the /activate and /deactivate business rules that the other maestros enforce."""
    resource = _make_resource(client, unique_name)
    rid = resource["id"]

    patched = client.patch(f"/api/resources/{rid}", json={"active": False, "notes": "still here"})
    assert patched.status_code == 200
    body = patched.get_json()
    assert body["active"] is True  # unaffected by the active field in the payload
    assert body["notes"] == "still here"


def test_deactivate_then_activate_resource_roundtrip(client, unique_name):
    """Regression: ResourceRepository.set_active was missing, so /activate returned 500."""
    resource = _make_resource(client, unique_name)
    rid = resource["id"]

    deactivated = client.patch(f"/api/resources/{rid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json()["active"] is False

    activated = client.patch(f"/api/resources/{rid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": rid, "active": True}


def test_resource_email_outside_domain_rejected(client, unique_name):
    resp = client.post("/api/resources", json={"full_name": "Bad Email", "email": f"{unique_name}@gmail.com"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_email_domain"


def test_skill_create_and_delete(client, unique_name):
    created = client.post("/api/skills", json={"code": f"TEST_{unique_name}", "label": "Test skill"})
    assert created.status_code == 201
    body = created.get_json()
    assert created.headers["Location"] == f"/api/skills/{body['id']}"

    deleted = client.delete(f"/api/skills/{body['id']}")
    assert deleted.status_code == 204


def test_skill_delete_blocked_while_assigned_to_active_resource(client, unique_name):
    skill = client.post("/api/skills", json={"code": f"USED_{unique_name}", "label": "Used skill"}).get_json()
    _make_resource(client, unique_name, skill_ids=[skill["id"]])

    resp = client.delete(f"/api/skills/{skill['id']}")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "skill_in_use"
    assert body["resource_count"] == 1
