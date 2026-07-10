"""Normalizador global de respuestas de error de la API (spec 013).

Garantiza que TODA respuesta JSON con status >= 400 salga con el contrato
estandar {success: false, message, code} (+ campo legado "error"), sin tocar
los returns existentes de las rutas (Constitucion, Principio VII).
Contrato: specs/013-manejo-errores-notificaciones/contracts/error-contract.md
"""
import json
import logging
from typing import Tuple

from flask import Flask, Response
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

GENERIC_500_MESSAGE = "Ocurrio un error interno. Intenta de nuevo mas tarde."

_DEFAULT_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}

_DEFAULT_MESSAGES = {
    400: "La solicitud no es valida.",
    401: "No autenticado. Inicia sesion de nuevo.",
    403: "No tienes permisos para realizar esta accion.",
    404: "El recurso solicitado no existe.",
    405: "Metodo no permitido para este recurso.",
    409: "La operacion entra en conflicto con el estado actual.",
    422: "Los datos enviados no son validos.",
}


def _default_code(status: int) -> str:
    if status in _DEFAULT_CODES:
        return _DEFAULT_CODES[status]
    return "INTERNAL_ERROR" if status >= 500 else "ERROR"


def _default_message(status: int) -> str:
    if status >= 500:
        return GENERIC_500_MESSAGE
    return _DEFAULT_MESSAGES.get(status, "Ocurrio un error procesando la solicitud.")


def normalize_error_response(response: Response) -> Response:
    """Hook after_request: aplica el contrato estandar a errores JSON (>= 400)."""
    if response.status_code < 400 or response.direct_passthrough:
        return response
    if not (response.mimetype or "").endswith("json"):
        return response
    payload = response.get_json(silent=True)
    if not isinstance(payload, dict):
        return response

    legacy_error = payload.get("error")
    code = payload.get("code")
    if not isinstance(code, str) or not code:
        if isinstance(legacy_error, str) and legacy_error:
            code = legacy_error.upper()
        else:
            code = _default_code(response.status_code)

    message = payload.get("message")
    has_valid_message = isinstance(message, str) and message.strip() != ""
    if response.status_code >= 500 and not isinstance(legacy_error, str):
        # 500 no controlado por una ruta: nunca exponer detalles internos.
        message = GENERIC_500_MESSAGE
    elif not has_valid_message:
        message = _default_message(response.status_code)

    payload["success"] = False
    payload["message"] = message
    payload["code"] = code
    payload.setdefault("error", code.lower())

    response.set_data(json.dumps(payload, ensure_ascii=False))
    response.mimetype = "application/json"
    return response


def register_error_handling(app: Flask) -> None:
    """Registra el normalizador y los manejadores globales en la app Flask."""
    app.after_request(normalize_error_response)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException) -> Tuple[dict, int]:
        # Las rutas no usan abort() con mensajes propios: la descripcion de
        # werkzeug viene en ingles, se reemplaza por el default en espanol.
        status = exc.code or 500
        code = _default_code(status)
        return {
            "success": False,
            "message": _default_message(status),
            "code": code,
            "error": code.lower(),
        }, status

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception) -> Tuple[dict, int]:
        logger.exception("Unhandled error handling API request")
        return {
            "success": False,
            "message": GENERIC_500_MESSAGE,
            "code": "INTERNAL_ERROR",
            "error": "server_error",
        }, 500
