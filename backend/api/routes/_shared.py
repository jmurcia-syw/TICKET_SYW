"""Utilities shared by the maestros CRUD namespaces (clients, projects, resources, users).

Kept here instead of duplicated per-file so error handling and ID parsing stay
consistent across the API as required by the api-design-principles skill.
"""
import logging
import uuid

from flask_restx import fields

logger = logging.getLogger(__name__)


def parse_uuid(value):
    """Parse a string into a UUID, returning None if invalid."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def error_model(ns, name="Error"):
    """Register the standard error schema on a namespace (spec 013 contract).

    El normalizador global (backend/api/errors.py) garantiza success/code en
    toda respuesta >= 400 aunque la ruta solo devuelva {error, message}.
    """
    return ns.model(name, {
        "success": fields.Boolean(description="Siempre false en errores", example=False),
        "message": fields.String(description="Descripcion del error, apta para usuario final"),
        "code": fields.String(description="Codigo estable UPPER_SNAKE_CASE", example="NOT_FOUND"),
        "error": fields.String(description="Codigo legado snake_case (deprecado)", example="not_found"),
    })


def server_error():
    """Log the real exception server-side, return a generic 500 payload to the client.

    Never surface str(exc) in the response body - it can leak internal details
    (SQL, file paths, stack info) to API consumers.
    """
    logger.exception("Unhandled error handling API request")
    return {"error": "server_error", "message": "Ocurrio un error interno. Intenta de nuevo mas tarde."}, 500
