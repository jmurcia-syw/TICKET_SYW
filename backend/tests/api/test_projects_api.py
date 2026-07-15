from datetime import date, timedelta

# OBS-0011: la fecha de inicio no puede estar en un mes anterior al actual al CREAR un
# proyecto — estos tests usan el primer día del mes en curso como fecha "válida" para no
# quedar rotos por el paso del tiempo.
_START = date.today().replace(day=1).isoformat()
_BEFORE_START = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
_PAST_MONTH_START = (date.today().replace(day=1) - timedelta(days=32)).replace(day=1).isoformat()


def _make_client(client, unique_name):
    return client.post("/api/clients", json={"name": f"ProjClient-{unique_name}"}).get_json()["id"]


def test_create_project_success_returns_201_with_location(client, unique_name):
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": _START,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/projects/{body['id']}"


def test_create_project_missing_client_returns_404(client, unique_name):
    """Regression: client_not_found used to be flattened into a blanket 409."""
    resp = client.post("/api/projects", json={
        "client_id": "00000000-0000-0000-0000-000000000099",
        "name": f"Proj-{unique_name}", "start_date": _START,
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "client_not_found"


def test_create_project_invalid_dates_returns_400(client, unique_name):
    """Regression: invalid_dates used to be flattened into a blanket 409."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}",
        "start_date": _START, "end_date_estimated": _BEFORE_START,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_dates"


def test_create_project_duplicate_name_for_client_returns_409(client, unique_name):
    cid = _make_client(client, unique_name)
    payload = {"client_id": cid, "name": f"Proj-{unique_name}", "start_date": _START}
    client.post("/api/projects", json=payload)
    dup = client.post("/api/projects", json=payload)
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "name_duplicate"


def test_create_project_name_with_special_chars_rejected(client, unique_name):
    """OBS-0010: nombre con caracteres especiales no permitidos (@#$%) es rechazado."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": "Proyecto @#$%", "start_date": _START,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_project_name_too_long_rejected(client, unique_name):
    """OBS-0010: nombre de más de 150 caracteres es rechazado."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": "A" * 151, "start_date": _START,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_project_same_day_start_end_rejected(client, unique_name):
    """OBS-0011: fecha de fin igual a la de inicio ya no se acepta (debe ser estrictamente posterior)."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}",
        "start_date": _START, "end_date_estimated": _START,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_dates"


def test_create_project_negative_sale_amount_rejected(client, unique_name):
    """OBS-0012: valor monetario negativo se rechaza con mensaje (no se reemplaza por 0)."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": _START,
        "sale_services_usd": -500,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_project_start_date_in_past_month_rejected(client, unique_name):
    """OBS-0011: crear un proyecto con fecha de inicio en un mes anterior al actual se rechaza."""
    cid = _make_client(client, unique_name)
    resp = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": _PAST_MONTH_START,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_start_date"


def test_edit_project_does_not_revalidate_start_date_month(client, unique_name):
    """OBS-0011: la regla de mes solo aplica en creación — editar un proyecto ya cargado con
    fecha de inicio retroactiva (carga histórica legítima) no debe romperse al hacer PATCH."""
    cid = _make_client(client, unique_name)
    project = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": _START,
    }).get_json()
    resp = client.patch(f"/api/projects/{project['id']}", json={"start_date": _PAST_MONTH_START})
    assert resp.status_code == 200
    assert resp.get_json()["start_date"] == _PAST_MONTH_START


def test_deactivate_then_activate_project_roundtrip(client, unique_name):
    """Regression: ProjectRepository.set_active was missing, so /activate returned 500."""
    cid = _make_client(client, unique_name)
    project = client.post("/api/projects", json={
        "client_id": cid, "name": f"Proj-{unique_name}", "start_date": _START,
    }).get_json()
    pid = project["id"]

    deactivated = client.patch(f"/api/projects/{pid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json()["active"] is False

    activated = client.patch(f"/api/projects/{pid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": pid, "active": True}
