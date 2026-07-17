"""Motor de SLA dinámico (spec 022, Historia 2) — dominio puro, sin DB.

Único test automatizado de esta feature (directriz explícita del usuario / Principio VII de la
constitución): acotado a `sla_service.compute_available_seconds`/`compute_consumed_seconds`/
`compute_state`, con 5-10 registros dummy en memoria, sin correr la suite global de
integración. Cubre el escenario estricto del enunciado: jornada 8-18h, ticket entra a las 17h
con 1h disponible -> consume esa hora, pausa a las 18h, reanuda a las 8h del día siguiente.
"""
from datetime import date, datetime, time, timezone
import uuid

from backend.domain.entities.calendar import AbsenceRequest, Holiday, WorkScheduleSlot
from backend.domain.entities.resource import Resource
from backend.domain.entities.ticket import Ticket
from backend.domain.services import sla_service

RESOURCE_ID = uuid.uuid4()

# Miércoles 15 de julio de 2026 y jueves 16 (días consecutivos, jornada 08:00-18:00 en ambos).
SLOTS = [
    WorkScheduleSlot.create(RESOURCE_ID, weekday=2, start_time=time(8, 0), end_time=time(18, 0)),
    WorkScheduleSlot.create(RESOURCE_ID, weekday=3, start_time=time(8, 0), end_time=time(18, 0)),
]

TICKET_ENTRY = datetime(2026, 7, 15, 17, 0, tzinfo=timezone.utc)  # miércoles 17:00
END_OF_DAY = datetime(2026, 7, 15, 18, 30, tzinfo=timezone.utc)   # miércoles 18:30 (fuera de horario)
NEXT_DAY_MORNING = datetime(2026, 7, 16, 9, 0, tzinfo=timezone.utc)  # jueves 09:00


def _resource(**overrides) -> Resource:
    defaults = dict(id=RESOURCE_ID, full_name="Resolutor Test", email="r@sywork.net",
                    timezone="UTC", calendar_country="CO")
    defaults.update(overrides)
    return Resource(**defaults)


def _ticket(**overrides) -> Ticket:
    defaults = dict(
        id=uuid.uuid4(), ticket_number=1, title="t", description="d",
        ticket_type="incident", priority="critical", severity="s1",
        client_id=uuid.uuid4(), created_by=uuid.uuid4(), status="en_ejecucion",
        assignee_id=RESOURCE_ID, sla_phase="ejecucion", sla_phase_limit_minutes=480,
        sla_consumed_seconds=0, sla_last_resume_at=TICKET_ENTRY, sla_status="corriendo",
    )
    defaults.update(overrides)
    return Ticket(**defaults)


def test_ticket_entra_con_una_hora_disponible_consume_solo_esa_hora():
    """Escenario estricto del enunciado: jornada 8-18h, ticket entra a las 17h -> consume 1h."""
    resource = _resource()
    seconds = sla_service.compute_available_seconds(
        resource, TICKET_ENTRY, END_OF_DAY, holidays=[], schedule_slots=SLOTS, absences=[])
    assert seconds == 3600


def test_pausa_automatica_fuera_de_horario_sin_persistir_nada():
    """El estado de lectura pasa a 'pausado'/'outside_hours' sin tocar sla_status persistido."""
    ticket = _ticket()
    resource = _resource()
    state = sla_service.compute_state(
        ticket, END_OF_DAY, resource=resource, holidays=[], schedule_slots=SLOTS, absences=[])
    assert state["status"] == "pausado"
    assert state["pause_reason"] == "outside_hours"
    assert state["consumed_seconds"] == 3600
    assert ticket.sla_status == "corriendo"  # el snapshot persistido no se modifica


def test_reanuda_automaticamente_al_dia_siguiente_a_las_8h():
    """El contador retoma solo, sin ningún proceso en segundo plano (research.md Decisión 5)."""
    resource = _resource()
    seconds = sla_service.compute_available_seconds(
        resource, TICKET_ENTRY, NEXT_DAY_MORNING, holidays=[], schedule_slots=SLOTS, absences=[])
    # 1h del miércoles (17-18h) + 1h del jueves (8-9h) = 2h
    assert seconds == 7200


def test_ticket_recibido_fuera_de_horario_no_descuenta_tiempo():
    """Un ticket que entra a las 19h (fuera de la jornada 8-18h) no consume SLA hasta la
    siguiente ventana disponible."""
    resource = _resource()
    entry_after_hours = datetime(2026, 7, 15, 19, 0, tzinfo=timezone.utc)
    still_after_hours = datetime(2026, 7, 15, 23, 0, tzinfo=timezone.utc)
    seconds = sla_service.compute_available_seconds(
        resource, entry_after_hours, still_after_hours, holidays=[], schedule_slots=SLOTS, absences=[])
    assert seconds == 0


def test_festivo_oficial_bloquea_toda_la_disponibilidad_del_dia():
    resource = _resource()
    holiday = Holiday.create("CO", date(2026, 7, 15), "Festivo de prueba", category="oficial")
    seconds = sla_service.compute_available_seconds(
        resource, TICKET_ENTRY, END_OF_DAY, holidays=[holiday], schedule_slots=SLOTS, absences=[])
    assert seconds == 0


def test_ausencia_parcial_por_horas_descuenta_solo_ese_tramo():
    """FR-017: un permiso de 17:00 a 17:30 dentro de la ventana 17:00-18:30 deja solo 30 min
    disponibles en vez de la hora completa."""
    resource = _resource()
    absence = AbsenceRequest.create(
        RESOURCE_ID, uuid.uuid4(), date(2026, 7, 15), date(2026, 7, 15),
        manager_status="approved", start_time=time(17, 0), end_time=time(17, 30),
    )
    absence.hr_status = "approved"
    seconds = sla_service.compute_available_seconds(
        resource, TICKET_ENTRY, END_OF_DAY, holidays=[], schedule_slots=SLOTS, absences=[absence])
    assert seconds == 1800


def test_sin_contexto_preserva_wall_clock_puro():
    """Sin resource/holidays/schedule_slots (parámetros opcionales), se conserva el
    comportamiento wall-clock original — no rompe llamadores no migrados (research.md
    Decisión 10)."""
    ticket = _ticket()
    consumed = sla_service.compute_consumed_seconds(ticket, END_OF_DAY)
    assert consumed == int((END_OF_DAY - TICKET_ENTRY).total_seconds())
