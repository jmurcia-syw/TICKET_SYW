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


def test_create_resource_invalid_identification_rejected(client, unique_name):
    """OBS-0020: 'identification' debe ser solo dígitos (6 a 15)."""
    resp = client.post("/api/resources", json={
        "full_name": f"Resource {unique_name}", "email": f"res.{unique_name}@sywork.net",
        "identification": "AB#12!@$99",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_resource_underage_birth_date_rejected(client, unique_name):
    """OBS-0022: fecha de nacimiento que implica menos de 18 años se rechaza."""
    resp = client.post("/api/resources", json={
        "full_name": f"Resource {unique_name}", "email": f"res.{unique_name}@sywork.net",
        "birth_date": "2020-01-01",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_resource_future_birth_date_rejected(client, unique_name):
    resp = client.post("/api/resources", json={
        "full_name": f"Resource {unique_name}", "email": f"res.{unique_name}@sywork.net",
        "birth_date": "2099-01-01",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


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


def test_patch_links_existing_user_to_resource(client, unique_name, resolver_user):
    """Recurso ya creado sin cuenta -> vincular una cuenta existente vía PATCH."""
    resource = _make_resource(client, unique_name)
    rid = resource["id"]

    patched = client.patch(f"/api/resources/{rid}", json={"user_id": str(resolver_user.id)})
    assert patched.status_code == 200
    assert patched.get_json()["user_id"] == str(resolver_user.id)


def test_patch_rejects_user_id_already_linked_to_another_resource(client, unique_name, resolver_user):
    first = _make_resource(client, unique_name)
    client.patch(f"/api/resources/{first['id']}", json={"user_id": str(resolver_user.id)})

    second = _make_resource(client, f"{unique_name}b")
    resp = client.patch(f"/api/resources/{second['id']}", json={"user_id": str(resolver_user.id)})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "user_already_linked"


def test_patch_unlinks_user_with_null(client, unique_name, resolver_user):
    resource = _make_resource(client, unique_name)
    rid = resource["id"]
    client.patch(f"/api/resources/{rid}", json={"user_id": str(resolver_user.id)})

    unlinked = client.patch(f"/api/resources/{rid}", json={"user_id": None})
    assert unlinked.status_code == 200
    assert unlinked.get_json()["user_id"] is None


def test_patch_rejects_unknown_user_id(client, unique_name):
    resource = _make_resource(client, unique_name)
    resp = client.patch(f"/api/resources/{resource['id']}", json={"user_id": "00000000-0000-0000-0000-000000000099"})
    assert resp.status_code == 404


def test_resource_email_outside_domain_rejected(client, unique_name):
    resp = client.post("/api/resources", json={"full_name": "Bad Email", "email": f"{unique_name}@gmail.com"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_email_domain"


def test_skill_create_and_delete(client, unique_name):
    created = client.post("/api/skills", json={"code": f"TEST_{unique_name}", "label": "Test skill", "skill_type": "tecnico"})
    assert created.status_code == 201
    body = created.get_json()
    assert created.headers["Location"] == f"/api/skills/{body['id']}"

    deleted = client.delete(f"/api/skills/{body['id']}")
    assert deleted.status_code == 204


def test_skill_delete_blocked_while_assigned_to_active_resource(client, unique_name):
    skill = client.post("/api/skills", json={"code": f"USED_{unique_name}", "label": "Used skill", "skill_type": "tecnico"}).get_json()
    _make_resource(client, unique_name, skill_ids=[skill["id"]])

    resp = client.delete(f"/api/skills/{skill['id']}")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "skill_in_use"
    assert body["resource_count"] == 1
