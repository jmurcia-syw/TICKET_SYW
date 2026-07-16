"""Orquestación de sincronización de festivos oficiales (spec 021, research.md Decisión 2).

Capa de infraestructura (Capa 2) — combina el cliente HTTP externo (`holiday_api_client`) con los
repositorios (`HolidayRepository`, `HolidaySyncStatusRepository`). Reutilizada tanto por el
intento inline del endpoint `GET /api/holidays` como por la tarea periódica de Celery
(`backend/workers/holiday_sync_tasks.py`), evitando duplicar esta lógica en dos lugares.
"""
import logging

from sqlalchemy.orm import Session

from backend.infra.external.holiday_api_client import HolidayApiError, fetch_public_holidays
from backend.infra.repositories.calendar_repo import HolidayRepository, HolidaySyncStatusRepository

logger = logging.getLogger(__name__)


def sync_country(db: Session, country: str, year: int) -> bool:
    """Sincroniza los festivos oficiales de `country` para `year` desde la fuente externa.

    Devuelve `True` si la sincronización fue exitosa (con o sin festivos nuevos insertados),
    `False` si la fuente externa falló — nunca lanza excepción (FR-003: no debe bloquear otra
    funcionalidad; el llamador decide qué hacer con un `False`)."""
    holiday_repo = HolidayRepository(db)
    status_repo = HolidaySyncStatusRepository(db)
    try:
        external_holidays = fetch_public_holidays(country, year)
    except HolidayApiError as e:
        logger.warning("sync_country failed for %s/%s: %s", country, year, e)
        status_repo.record_attempt(country, year, success=False, error_message=str(e))
        return False

    for item in external_holidays:
        holiday_repo.upsert_api_holiday(country, item["holiday_date"], item["name"], category="oficial")
    status_repo.record_attempt(country, year, success=True)
    return True
