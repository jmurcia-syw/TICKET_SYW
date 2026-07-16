"""Cliente HTTP para la API pública de festivos date.nager.at (spec 021, research.md Decisión 1).

Capa de infraestructura (Capa 2) — solo obtiene datos crudos de un servicio externo, sin lógica
de negocio ni decisiones de categoría/origen (eso vive en `holiday_sync_service.py`). Servicio
público y gratuito, sin API key.
"""
from datetime import date
from typing import TypedDict

import requests

_BASE_URL = "https://date.nager.at/api/v3/PublicHolidays"
_TIMEOUT_SECONDS = 3


class HolidayApiError(Exception):
    """La fuente externa de festivos no respondió correctamente. El llamador decide cómo
    degradar (FR-003: nunca debe bloquear otra funcionalidad del sistema)."""


class ExternalHoliday(TypedDict):
    holiday_date: date
    name: str


def fetch_public_holidays(country: str, year: int) -> list[ExternalHoliday]:
    """Festivos oficiales de `country` (ISO 3166-1 alpha-2) para `year`.

    Lanza `HolidayApiError` si la fuente externa no responde, responde con error, o el país no
    está soportado (404 "Unknown country code")."""
    try:
        response = requests.get(f"{_BASE_URL}/{year}/{country}", timeout=_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise HolidayApiError(f"No se pudo contactar la fuente de festivos: {e}") from e
    if response.status_code != 200:
        raise HolidayApiError(
            f"Fuente de festivos respondió {response.status_code} para {country}/{year}")
    try:
        payload = response.json()
    except ValueError as e:
        raise HolidayApiError(f"Respuesta inválida de la fuente de festivos: {e}") from e
    return [
        {"holiday_date": date.fromisoformat(item["date"]), "name": item.get("localName") or item["name"]}
        for item in payload
    ]
