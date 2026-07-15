"""Accesos y conexiones múltiples del Cliente (spec 018, UAT OBS-0001/OBS-0008/OBS-0017).

Tests ultra-limitados (Principio VII): un único cliente de fixture, ≤10 registros de acceso
por test, sin crear usuarios Resolutor adicionales (se reutiliza `resolver_token`, ya semilla).
"""
import io


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_add_multiple_access_types_and_attachment(client, unique_name):
    """US1 (OBS-0001): tres tipos de acceso distintos + un adjunto persisten por separado."""
    created = client.post("/api/clients", json={"name": f"Client-{unique_name}"}).get_json()
    cid = created["id"]

    vpn = client.post(f"/api/clients/{cid}/access", json={
        "access_type": "vpn", "username": "vpnuser", "password": "vpnpass", "host": "10.0.0.5",
    })
    assert vpn.status_code == 201, vpn.get_json()

    url = client.post(f"/api/clients/{cid}/access", json={
        "access_type": "system_url", "environment": "test",
        "username": "sysuser", "password": "syspass", "host": "https://test.acme.com",
    })
    assert url.status_code == 201, url.get_json()

    rdp = client.post(f"/api/clients/{cid}/access", json={
        "access_type": "remote_desktop", "host": "RDP-ACME-01",
    })
    assert rdp.status_code == 201, rdp.get_json()

    listed = client.get(f"/api/clients/{cid}/access")
    assert listed.status_code == 200
    items = listed.get_json()["items"]
    assert len(items) == 3
    assert {i["access_type"] for i in items} == {"vpn", "system_url", "remote_desktop"}

    upload = client.post(
        f"/api/clients/{cid}/access-attachments",
        data={"file": (io.BytesIO(b"contenido de prueba"), "instructivo.txt")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201, upload.get_json()
    attachments = client.get(f"/api/clients/{cid}/access-attachments").get_json()["items"]
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "instructivo.txt"


def test_update_and_delete_access_does_not_affect_others(client, unique_name):
    """US1: editar/eliminar un registro no afecta a los demás del mismo cliente."""
    created = client.post("/api/clients", json={"name": f"Client-{unique_name}"}).get_json()
    cid = created["id"]

    a1 = client.post(f"/api/clients/{cid}/access", json={"access_type": "vpn", "host": "1.1.1.1"}).get_json()
    a2 = client.post(f"/api/clients/{cid}/access", json={"access_type": "remote_desktop", "host": "RDP-1"}).get_json()

    patched = client.patch(f"/api/clients/{cid}/access/{a1['id']}", json={"notes": "actualizado"})
    assert patched.status_code == 200
    assert patched.get_json()["notes"] == "actualizado"

    deleted = client.delete(f"/api/clients/{cid}/access/{a1['id']}")
    assert deleted.status_code == 204

    remaining = client.get(f"/api/clients/{cid}/access").get_json()["items"]
    assert len(remaining) == 1
    assert remaining[0]["id"] == a2["id"]


def test_invalid_environment_for_non_system_url_rejected(client, unique_name):
    """FR-001: 'environment' solo aplica a access_type='system_url'."""
    created = client.post("/api/clients", json={"name": f"Client-{unique_name}"}).get_json()
    cid = created["id"]
    resp = client.post(f"/api/clients/{cid}/access", json={
        "access_type": "vpn", "environment": "test", "host": "1.1.1.1",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_access_isolated_between_two_clients(client, unique_name):
    """US2 (OBS-0008): los accesos de un cliente nunca aparecen en el listado de otro."""
    client_a = client.post("/api/clients", json={"name": f"Client-A-{unique_name}"}).get_json()
    client_b = client.post("/api/clients", json={"name": f"Client-B-{unique_name}"}).get_json()

    client.post(f"/api/clients/{client_a['id']}/access", json={"access_type": "vpn", "host": "A-host"})

    items_b = client.get(f"/api/clients/{client_b['id']}/access").get_json()["items"]
    assert items_b == []

    items_a = client.get(f"/api/clients/{client_a['id']}/access").get_json()["items"]
    assert len(items_a) == 1
    assert items_a[0]["host"] == "A-host"


def test_password_hidden_without_sensitive_permission(anon_client, client, unique_name, resolver_token):
    """US3 (OBS-0017): sin permiso de datos sensibles, no se expone username/password."""
    created = client.post("/api/clients", json={"name": f"Client-{unique_name}"}).get_json()
    cid = created["id"]
    client.post(f"/api/clients/{cid}/access", json={
        "access_type": "vpn", "username": "secretuser", "password": "secretpass", "host": "1.1.1.1",
    })

    as_resolver = anon_client.get(f"/api/clients/{cid}/access", headers=_auth(resolver_token))
    assert as_resolver.status_code == 200
    item = as_resolver.get_json()["items"][0]
    assert "password" not in item
    assert "username" not in item
    assert item["access_type"] == "vpn"

    as_admin = client.get(f"/api/clients/{cid}/access").get_json()["items"][0]
    assert as_admin["password"] == "secretpass"
    assert as_admin["username"] == "secretuser"
