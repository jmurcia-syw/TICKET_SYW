def _make_client(client, unique_name):
    return client.post("/api/clients", json={"name": f"ProjClient-{unique_name}"}).get_json()["id"]


def test_create_project_success_returns_201_with_location(client, unique_name):
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": "2026-01-01",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/projects/{body['id']}"


def test_create_project_missing_client_returns_404(client, unique_name):
    """Regression: client_not_found used to be flattened into a blanket 409."""
    resp = client.post("/api/projects", json={
        "client_id": "00000000-0000-0000-0000-000000000099",
        "name": f"Proj-{unique_name}", "start_date": "2026-01-01",
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "client_not_found"


def test_create_project_invalid_dates_returns_400(client, unique_name):
    """Regression: invalid_dates used to be flattened into a blanket 409."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}",
        "start_date": "2026-06-01", "end_date_estimated": "2026-01-01",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_dates"


def test_create_project_duplicate_name_for_client_returns_409(client, unique_name):
    cid = _make_client(client, unique_name)
    payload = {"client_id": cid, "name": f"Proj-{unique_name}", "start_date": "2026-01-01"}
    client.post("/api/projects", json=payload)
    dup = client.post("/api/projects", json=payload)
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "name_duplicate"


def test_deactivate_then_activate_project_roundtrip(client, unique_name):
    """Regression: ProjectRepository.set_active was missing, so /activate returned 500."""
    cid = _make_client(client, unique_name)
    project = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": "2026-01-01",
    }).get_json()
    pid = project["id"]

    deactivated = client.patch(f"/api/projects/{pid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json()["active"] is False

    activated = client.patch(f"/api/projects/{pid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": pid, "active": True}
