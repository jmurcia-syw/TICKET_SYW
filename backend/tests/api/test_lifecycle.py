"""US3 — Ciclo de vida completo por comentarios tipificados (Escenario 4 del quickstart)."""
import io

import pytest


@pytest.fixture()
def assigned_ticket(client, make_ticket, ticket_resource):
    """Ticket en CONTACTO asignado al recurso del resolutor de prueba."""
    ticket = make_ticket()
    response = client.post(f"/api/tickets/{ticket['id']}/assign",
                           json={"assignee_id": ticket_resource["id"], "mode": "resolver"})
    assert response.status_code == 200
    return ticket


def _comment(client, ticket_id, comment_type, body="avance", headers=None):
    return client.post(f"/api/tickets/{ticket_id}/comments",
                       json={"comment_type": comment_type, "body": body},
                       headers=headers)


def _resolution_type_id(client):
    items = client.get("/api/catalogs/resolution-types").get_json()["items"]
    return items[0]["id"]


def test_happy_path_full_lifecycle(client, assigned_ticket):
    tid = assigned_ticket["id"]
    # CONTACTO → EN ANÁLISIS
    r = _comment(client, tid, "confirmacion_atencion", "Contacté al usuario")
    assert r.status_code == 201 and r.get_json()["ticket"]["status"] == "en_analisis"
    # tiempo estimado editable en EN ANÁLISIS (FR-010)
    r = client.patch(f"/api/tickets/{tid}", json={"estimated_resolution_minutes": 240})
    assert r.status_code == 200
    # EN ANÁLISIS → EN EJECUCIÓN
    r = _comment(client, tid, "termina_analisis", "Diagnóstico: parche en la orquestación")
    assert r.get_json()["ticket"]["status"] == "en_ejecucion"
    # tiempo bloqueado en EN EJECUCIÓN
    r = client.patch(f"/api/tickets/{tid}", json={"estimated_resolution_minutes": 300})
    assert r.status_code == 409 and r.get_json()["error"] == "field_locked"
    # EN EJECUCIÓN → PENDIENTE DE USUARIO → EN EJECUCIÓN
    assert _comment(client, tid, "solicitud_informacion").get_json()["ticket"]["status"] == "pendiente_usuario"
    assert _comment(client, tid, "respuesta_usuario").get_json()["ticket"]["status"] == "en_ejecucion"
    # EN PRUEBAS toggle (Q1)
    r = client.post(f"/api/tickets/{tid}/testing", json={"direction": "enter"})
    assert r.get_json()["status"] == "en_pruebas"
    r = client.post(f"/api/tickets/{tid}/testing", json={"direction": "exit"})
    assert r.get_json()["status"] == "en_ejecucion"
    # EN EJECUCIÓN → RESUELTO
    assert _comment(client, tid, "solicitud_cierre").get_json()["ticket"]["status"] == "resuelto"
    # cierre sin aceptación ni 3 días → bloqueado
    r = client.post(f"/api/tickets/{tid}/close",
                    json={"resolution_type_id": _resolution_type_id(client), "body": "fix"})
    assert r.status_code == 409
    # aceptación (Q2) y cierre
    r = client.post(f"/api/tickets/{tid}/resolution", json={"accepted": True})
    assert r.status_code == 200 and r.get_json()["close_eligible"] is True
    r = client.post(f"/api/tickets/{tid}/close",
                    json={"resolution_type_id": _resolution_type_id(client),
                          "body": "Se aplicó el parche y se validó con el usuario"})
    assert r.status_code == 200
    detail = r.get_json()
    assert detail["status"] == "cerrado"
    assert detail["closed_at"] is not None
    # historial completo con autor y comentario por transición
    assert len(detail["transitions"]) >= 8
    assert all(t["actor_id"] for t in detail["transitions"])


def test_invalid_comment_for_state_is_409_with_valid_actions(client, make_ticket):
    ticket = make_ticket()  # NUEVO sin asignar
    response = _comment(client, ticket["id"], "confirmacion_atencion")
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "invalid_transition"
    assert "Acciones válidas" in data["message"]


def test_resolution_rejected_returns_to_execution(client, assigned_ticket):
    tid = assigned_ticket["id"]
    _comment(client, tid, "confirmacion_atencion")
    _comment(client, tid, "termina_analisis")
    _comment(client, tid, "solicitud_cierre")
    response = client.post(f"/api/tickets/{tid}/resolution",
                           json={"accepted": False, "body": "El error persiste"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "en_ejecucion"


def test_resolver_cannot_transition_foreign_ticket(client, make_ticket, unique_name,
                                                   resolver_auth, anon_client):
    # ticket asignado a OTRO recurso (sin user vinculado)
    other = client.post("/api/resources", json={
        "full_name": f"Otro Res {unique_name}",
        "email": f"otro.{unique_name}@sywork.net",
    }).get_json()
    ticket = make_ticket()
    client.post(f"/api/tickets/{ticket['id']}/assign",
                json={"assignee_id": other["id"], "mode": "resolver"})
    response = _comment(anon_client, ticket["id"], "confirmacion_atencion",
                        headers=resolver_auth)
    assert response.status_code == 403


def test_comment_with_attachment(client, assigned_ticket):
    tid = assigned_ticket["id"]
    data = {
        "comment_type": "confirmacion_atencion",
        "body": "Contacto realizado, adjunto evidencia",
        "files": (io.BytesIO(b"contenido de log"), "evidencia.log"),
    }
    response = client.post(f"/api/tickets/{tid}/comments", data=data,
                           content_type="multipart/form-data")
    assert response.status_code == 201, response.get_json()
    comment = response.get_json()["comment"]
    assert len(comment["attachments"]) == 1
    att = comment["attachments"][0]
    # descarga autenticada
    download = client.get(f"/api/tickets/{tid}/attachments/{att['id']}")
    assert download.status_code == 200
    assert download.data == b"contenido de log"


def test_attachment_type_not_allowed(client, assigned_ticket):
    data = {
        "comment_type": "comentario_interno",
        "body": "intento con ejecutable",
        "files": (io.BytesIO(b"MZ"), "virus.exe"),
    }
    response = client.post(f"/api/tickets/{assigned_ticket['id']}/comments", data=data,
                           content_type="multipart/form-data")
    assert response.status_code == 400
    assert "no permitido" in response.get_json()["message"]


def test_cancel_requires_reason_and_permission(client, make_ticket, qm_token, anon_client):
    ticket = make_ticket()
    # sin motivo → 400
    assert client.post(f"/api/tickets/{ticket['id']}/cancel", json={}).status_code == 400
    # QM sin permiso cancel → 403
    response = anon_client.post(f"/api/tickets/{ticket['id']}/cancel",
                                json={"body": "x"},
                                headers={"Authorization": f"Bearer {qm_token}"})
    assert response.status_code == 403
    # Admin con motivo → cancelado
    response = client.post(f"/api/tickets/{ticket['id']}/cancel",
                           json={"body": "Duplicado del TK-000001"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "cancelado"
