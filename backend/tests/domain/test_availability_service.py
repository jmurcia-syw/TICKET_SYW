"""availability_service — dominio puro, sin DB (spec 020, Fase 5).

Ultra-limitado (Principio VII): fixtures en memoria, sin inserts a base de datos.
"""
from datetime import date, datetime, time, timezone
import uuid

from backend.domain.entities.calendar import Holiday, WorkScheduleSlot, AbsenceRequest
from backend.domain.entities.resource import Resource
from backend.domain.services.availability_service import compute_availability

RESOURCE_ID = uuid.uuid4()
# Miércoles 15 de julio de 2026, 10:00 UTC — dentro del horario por defecto (lun-vie 08-17).
WEEKDAY_MORNING = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)
# Mismo día, 22:00 UTC — fuera del horario por defecto.
WEEKDAY_NIGHT = datetime(2026, 7, 15, 22, 0, tzinfo=timezone.utc)


def _resource(**overrides) -> Resource:
    defaults = dict(id=RESOURCE_ID, full_name="Resolutor Test", email="r@sywork.net")
    defaults.update(overrides)
    return Resource(**defaults)


def test_sin_timezone_ni_pais_es_disponible_por_defecto():
    """FR-016: sin ningún dato de calendario configurado, nunca se penaliza."""
    resource = _resource()
    result = compute_availability(resource, WEEKDAY_NIGHT, holidays=[], work_schedule_slots=[], active_absence=None)
    assert result.available is True
    assert result.reason is None


def test_ausencia_aprobada_prevalece_incluso_sin_otra_configuracion():
    """La ausencia es dato explícito: cuenta incluso sin timezone/país (FR-013)."""
    resource = _resource()
    absence = AbsenceRequest.create(resource.id, uuid.uuid4(), date(2026, 7, 15), date(2026, 7, 16))
    result = compute_availability(resource, WEEKDAY_NIGHT, holidays=[], work_schedule_slots=[], active_absence=absence)
    assert result.available is False
    assert result.reason == "absence"


def test_festivo_del_pais_configurado_marca_no_disponible():
    resource = _resource(timezone="UTC", calendar_country="CO")
    holiday = Holiday.create("CO", date(2026, 7, 15), "Festivo de prueba")
    result = compute_availability(resource, WEEKDAY_MORNING, holidays=[holiday], work_schedule_slots=[], active_absence=None)
    assert result.available is False
    assert result.reason == "holiday"
    assert result.detail == "Festivo de prueba"


def test_dentro_del_horario_por_defecto_sin_festivo_es_disponible():
    resource = _resource(timezone="UTC", calendar_country="CO")
    result = compute_availability(resource, WEEKDAY_MORNING, holidays=[], work_schedule_slots=[], active_absence=None)
    assert result.available is True


def test_fuera_del_horario_por_defecto_marca_no_disponible():
    resource = _resource(timezone="UTC", calendar_country="CO")
    result = compute_availability(resource, WEEKDAY_NIGHT, holidays=[], work_schedule_slots=[], active_absence=None)
    assert result.available is False
    assert result.reason == "outside_hours"


def test_horario_custom_reemplaza_al_default():
    """Con franjas propias, una franja nocturna hace disponible una hora que el default rechazaría."""
    resource = _resource(timezone="UTC")
    slot = WorkScheduleSlot.create(resource.id, weekday=2, start_time=time(20, 0), end_time=time(23, 0))
    result = compute_availability(resource, WEEKDAY_NIGHT, holidays=[], work_schedule_slots=[slot], active_absence=None)
    assert result.available is True
