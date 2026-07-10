"""Tests del normalizador global de errores (spec 013).

Unit tests puros sobre una app Flask minima: sin base de datos, sin fixtures
de datos. 8 casos simulados (limite constitucional: 5-10 por Principio VII).
Ejecutar SOLO este archivo: pytest backend/tests/test_error_contract.py
"""
import pytest
from flask import Flask, abort

from backend.api.errors import GENERIC_500_MESSAGE, register_error_handling


@pytest.fixture(scope="module")
def error_client():
    app = Flask(__name__)
    register_error_handling(app)

    @app.get("/ok")
    def ok():
        return {"success": True, "items": []}

    @app.get("/legacy-400")
    def legacy_400():
        return {"error": "ticket_not_assigned", "message": "El ticket no esta asignado a este proyecto"}, 400

    @app.get("/legacy-403")
    def legacy_403():
        return {"error": "forbidden", "message": "No tienes el permiso tickets:edit"}, 403

    @app.get("/bare-404")
    def bare_404():
        return {}, 404

    @app.get("/controlled-500")
    def controlled_500():
        return {"error": "server_error", "message": "Ocurrio un error interno. Intenta de nuevo mas tarde."}, 500

    @app.get("/boom")
    def boom():
        raise RuntimeError("secreto interno: SELECT * FROM users")

    @app.get("/abort-404")
    def abort_404():
        abort(404)

    @app.get("/with-code")
    def with_code():
        return {"code": "CUSTOM_CODE", "message": "Mensaje propio"}, 400

    return app.test_client()


def test_success_response_untouched(error_client):
    resp = error_client.get("/ok")
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "items": []}


def test_legacy_error_gets_success_and_code(error_client):
    resp = error_client.get("/legacy-400")
    body = resp.get_json()
    assert resp.status_code == 400
    assert body["success"] is False
    assert body["code"] == "TICKET_NOT_ASSIGNED"
    assert body["message"] == "El ticket no esta asignado a este proyecto"
    assert body["error"] == "ticket_not_assigned"  # legado conservado


def test_403_keeps_message_and_derives_code(error_client):
    body = error_client.get("/legacy-403").get_json()
    assert body["success"] is False
    assert body["code"] == "FORBIDDEN"
    assert body["message"] == "No tienes el permiso tickets:edit"


def test_bare_404_gets_defaults(error_client):
    resp = error_client.get("/bare-404")
    body = resp.get_json()
    assert resp.status_code == 404
    assert body["success"] is False
    assert body["code"] == "NOT_FOUND"
    assert isinstance(body["message"], str) and body["message"]


def test_controlled_500_keeps_route_message(error_client):
    body = error_client.get("/controlled-500").get_json()
    assert body["success"] is False
    assert body["code"] == "SERVER_ERROR"
    assert body["message"] == "Ocurrio un error interno. Intenta de nuevo mas tarde."


def test_unhandled_exception_is_generic_500(error_client):
    resp = error_client.get("/boom")
    body = resp.get_json()
    assert resp.status_code == 500
    assert body == {
        "success": False,
        "message": GENERIC_500_MESSAGE,
        "code": "INTERNAL_ERROR",
        "error": "server_error",
    }
    assert "secreto" not in resp.get_data(as_text=True)
    assert "SELECT" not in resp.get_data(as_text=True)


def test_http_exception_standardized(error_client):
    resp = error_client.get("/abort-404")
    body = resp.get_json()
    assert resp.status_code == 404
    assert body["success"] is False
    assert body["code"] == "NOT_FOUND"


def test_explicit_code_preserved(error_client):
    body = error_client.get("/with-code").get_json()
    assert body["code"] == "CUSTOM_CODE"
    assert body["message"] == "Mensaje propio"
    assert body["success"] is False
