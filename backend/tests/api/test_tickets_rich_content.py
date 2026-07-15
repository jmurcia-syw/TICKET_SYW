"""spec 017 — Contenido enriquecido (formato, imágenes pegadas y adjuntos) en comentarios y
descripción de Ticket/Tarea.

Fixtures acotados al flujo (Cliente/Proyecto/Ticket ya existentes vía `make_ticket`) — sin
usuarios Resolutor adicionales ni disparo del correo de contraseña (misma restricción de
specs 015/016).
"""
import io


# ── US1: formato de texto (negrilla/cursiva/listas/hipervínculos), saneado server-side ──────

def test_comment_with_bold_and_link_keeps_allowed_tags(client, make_ticket):
    ticket = make_ticket()
    resp = client.post(f"/api/tickets/{ticket['id']}/comments", json={
        "comment_type": "comentario_interno",
        "body": '<p><strong>negrilla</strong> <a href="https://example.com">link</a></p>',
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()["comment"]["body"]
    assert "<strong>negrilla</strong>" in body
    assert '<a href="https://example.com"' in body


def test_comment_html_empty_paragraph_rejected(client, make_ticket):
    ticket = make_ticket()
    resp = client.post(f"/api/tickets/{ticket['id']}/comments", json={
        "comment_type": "comentario_interno",
        "body": "<p><br></p>",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_comment_strips_script_and_event_handler(client, make_ticket):
    ticket = make_ticket()
    resp = client.post(f"/api/tickets/{ticket['id']}/comments", json={
        "comment_type": "comentario_interno",
        "body": '<p onclick="alert(1)">hola</p><script>alert(2)</script>',
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()["comment"]["body"]
    assert "onclick" not in body
    assert "<script>" not in body


def test_ticket_description_with_formatting_is_sanitized(client, ticket_client):
    resp = client.post("/api/tickets", json={
        "title": "Ticket con descripción enriquecida",
        "description": '<p><em>cursiva</em></p><ul><li>uno</li><li>dos</li></ul>',
        "ticket_type": "incident", "priority": "medium", "severity": "s3",
        "client_id": ticket_client["id"],
    })
    assert resp.status_code == 201, resp.get_json()
    description = resp.get_json()["description"]
    assert "<em>cursiva</em>" in description
    assert "<li>uno</li>" in description


def test_ticket_description_html_empty_rejected(client, ticket_client):
    resp = client.post("/api/tickets", json={
        "title": "Ticket con descripción vacía",
        "description": "<p></p>",
        "ticket_type": "incident", "priority": "medium", "severity": "s3",
        "client_id": ticket_client["id"],
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


# ── US2: pegar contenido con imágenes incrustadas (adjuntos reales vía data-pending-id) ─────

def test_comment_multipart_with_inline_image_resolves_pending_id(client, make_ticket):
    ticket = make_ticket()
    data = {
        "comment_type": "comentario_interno",
        "body": '<p>mira esta captura</p><img data-pending-id="0">',
        "inline_images": (io.BytesIO(b"fake-png-bytes"), "captura.png"),
    }
    resp = client.post(f"/api/tickets/{ticket['id']}/comments", data=data,
                       content_type="multipart/form-data")
    assert resp.status_code == 201, resp.get_json()
    comment = resp.get_json()["comment"]
    assert "data-pending-id" not in comment["body"]
    assert len(comment["attachments"]) == 1
    att = comment["attachments"][0]
    assert f"/api/tickets/{ticket['id']}/attachments/{att['id']}" in comment["body"]


def test_ticket_multipart_with_inline_image_in_description(client, ticket_client):
    data = {
        "title": "Ticket con imagen pegada en la descripción",
        "description": '<p>ver adjunto</p><img data-pending-id="0">',
        "ticket_type": "incident", "priority": "medium", "severity": "s3",
        "client_id": ticket_client["id"],
        "inline_images": (io.BytesIO(b"fake-png-bytes"), "captura.png"),
    }
    resp = client.post("/api/tickets", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert "data-pending-id" not in body["description"]
    assert len(body["description_attachments"]) == 1
    att = body["description_attachments"][0]
    assert f"/api/tickets/{body['id']}/attachments/{att['id']}" in body["description"]


def test_comment_multipart_invalid_inline_image_rejected(client, make_ticket):
    ticket = make_ticket()
    before = client.get(f"/api/tickets/{ticket['id']}").get_json()
    data = {
        "comment_type": "comentario_interno",
        "body": '<p>mira</p><img data-pending-id="0">',
        "inline_images": (io.BytesIO(b"MZ"), "virus.exe"),
    }
    resp = client.post(f"/api/tickets/{ticket['id']}/comments", data=data,
                       content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "attachment_error"
    after = client.get(f"/api/tickets/{ticket['id']}").get_json()
    assert len(after["comments"]) == len(before["comments"])


# ── US3: adjuntar archivos (no imagen) a la descripción del Ticket/Tarea ───────────────────

def test_ticket_multipart_with_manual_attachment(client, ticket_client):
    data = {
        "title": "Ticket con adjunto manual en la descripción",
        "description": "<p>ver PDF adjunto</p>",
        "ticket_type": "incident", "priority": "medium", "severity": "s3",
        "client_id": ticket_client["id"],
        "attachments": (io.BytesIO(b"contenido pdf"), "manual.pdf"),
    }
    resp = client.post("/api/tickets", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert len(body["description_attachments"]) == 1
    att = body["description_attachments"][0]
    assert att["filename"] == "manual.pdf"
    download = client.get(f"/api/tickets/{body['id']}/attachments/{att['id']}")
    assert download.status_code == 200
    assert download.data == b"contenido pdf"


def test_ticket_multipart_manual_attachment_type_not_allowed(client, ticket_client):
    data = {
        "title": "Ticket con adjunto no permitido",
        "description": "<p>ver adjunto</p>",
        "ticket_type": "incident", "priority": "medium", "severity": "s3",
        "client_id": ticket_client["id"],
        "attachments": (io.BytesIO(b"MZ"), "virus.exe"),
    }
    resp = client.post("/api/tickets", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "attachment_error"
