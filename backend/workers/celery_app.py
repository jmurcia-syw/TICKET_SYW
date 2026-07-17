"""Configuración mínima de la app Celery (Fase 4 SLA — spec 014, T002).

Celery + Redis ya estaban aprobados en la Constitución (Principio V) específicamente
para "SLA timers"; esta es su primera materialización real en el repo.
"""
import os

from celery import Celery
from celery.schedules import crontab

import backend.infra.models  # noqa: F401 — registra todos los modelos SQLAlchemy antes de usar el ORM

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("sywork", broker=REDIS_URL, backend=REDIS_URL,
                     include=["backend.workers.sla_tasks", "backend.workers.holiday_sync_tasks"])

celery_app.conf.beat_schedule = {
    "check-sla-breaches": {
        "task": "backend.workers.sla_tasks.check_sla_breaches",
        "schedule": crontab(minute="*/5"),
    },
    "sync-holidays": {
        "task": "backend.workers.holiday_sync_tasks.sync_holidays",
        "schedule": crontab(hour=3, minute=0),
    },
}
celery_app.conf.timezone = "UTC"
