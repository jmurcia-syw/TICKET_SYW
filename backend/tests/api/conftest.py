"""Fixtures compartidos de los tests de API de tickets."""
import uuid

import pytest


@pytest.fixture()
def ticket_client(client, unique_name):
    """Cliente (maestro) activo de prueba."""
    response = client.post("/api/clients", json={"name": f"Cliente Tickets {unique_name}"})
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture()
def ticket_resource(client, unique_name, resolver_user):
    """Recurso activo vinculado al usuario resolutor de prueba."""
    response = client.post("/api/resources", json={
        "full_name": f"Resolutor Tickets {unique_name}",
        "email": f"resolutor.tk.{unique_name}@sywork.net",
        "user_id": str(resolver_user.id),
    })
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture()
def make_ticket(client, ticket_client):
    """Factory de tickets en estado NUEVO."""
    def _make(**overrides):
        payload = {
            "title": "Error contabilizando en GL",
            "description": "El batch de contabilización falla con error 105",
            "ticket_type": "incident",
            "priority": "high",
            "severity": "s2",
            "client_id": ticket_client["id"],
            **overrides,
        }
        response = client.post("/api/tickets", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()
    return _make


@pytest.fixture()
def resolver_auth(app, resolver_user):
    """Header Authorization del usuario resolutor de prueba."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(resolver_user.id))
    return {"Authorization": f"Bearer {token}"}
