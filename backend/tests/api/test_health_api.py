def test_health_ok(client):
    resp = client.get("/health/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True


def test_health_reports_generic_message_on_db_failure(client, monkeypatch):
    """Regression: the health check used to leak the raw exception string
    (potentially DB host/driver internals) straight into the response body."""
    def _boom():
        raise RuntimeError("connection refused to internal-db-host:5432 user=admin")
        yield  # pragma: no cover - keeps this a generator like the real get_db

    monkeypatch.setattr("backend.infra.database.get_db", _boom)

    resp = client.get("/health/")
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["status"] == "degraded"
    assert body["database"]["connected"] is False
    assert "internal-db-host" not in body["database"]["error"]
