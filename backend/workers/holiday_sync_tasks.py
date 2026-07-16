"""Tarea periódica de sincronización de festivos oficiales (spec 021, research.md Decisión 2).

`sync_holidays` corre diariamente (ver `beat_schedule` en `celery_app.py`): recorre los países
realmente en uso hoy por Clientes/Recursos y sincroniza el año actual y el siguiente para cada
uno, reutilizando `holiday_sync_service.sync_country` (mismo código que el intento inline del
endpoint `GET /api/holidays`).

Capa de infraestructura (usa DB/repos) — mismo patrón que `sla_tasks.py` (spec 014).
"""
from datetime import datetime, timezone
import logging

from backend.infra.database import close_db, get_db
from backend.infra.external.holiday_sync_service import sync_country
from backend.infra.models.client_model import ClientModel
from backend.infra.models.resource_model import ResourceModel
from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _countries_in_use(db) -> set[str]:
    client_countries = {c for (c,) in db.query(ClientModel.country).filter(ClientModel.country.isnot(None)).distinct()}
    resource_countries = {
        c for (c,) in db.query(ResourceModel.calendar_country)
        .filter(ResourceModel.calendar_country.isnot(None)).distinct()
    }
    return client_countries | resource_countries


@celery_app.task(name="backend.workers.holiday_sync_tasks.sync_holidays")
def sync_holidays() -> int:
    """Devuelve la cantidad de sincronizaciones país/año exitosas en esta corrida."""
    db = get_db()
    try:
        year = datetime.now(timezone.utc).year
        success_count = 0
        for country in _countries_in_use(db):
            for target_year in (year, year + 1):
                if sync_country(db, country, target_year):
                    success_count += 1
        return success_count
    except Exception:
        logger.exception("sync_holidays failed")
        db.rollback()
        raise
    finally:
        close_db()
