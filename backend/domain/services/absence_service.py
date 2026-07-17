"""absence_service — dominio puro, sin DB (spec 020, Fase 5, Historia 2; permisos parciales por
horas spec 022, Historia 3, FR-017).

Reglas de la cadena de aprobación (Jefe directo + RRHH) — Decisión 4 de research.md.
Sin imports de Flask/SQLAlchemy (Principio I).
"""
from datetime import date, time
from typing import Optional
import uuid

from backend.domain.entities.calendar import AbsenceRequest


class AbsenceServiceError(Exception):
    def __init__(self, message: str, code: str = "validation_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def validate_date_range(start_date: date, end_date: date) -> None:
    """FR-009: el rango de la solicitud debe ser válido."""
    if end_date < start_date:
        raise AbsenceServiceError("La fecha de fin no puede ser anterior a la fecha de inicio")


def validate_partial_hours(start_date: date, end_date: date, start_time: Optional[time],
                           end_time: Optional[time]) -> None:
    """FR-017: un permiso parcial por horas (ej. cita médica de 2h, media jornada) es opcional
    — si se informa un lado (`start_time`/`end_time`), el otro también debe venir, el rango debe
    caer en un único día (`start_date == end_date`), y `start_time < end_time`."""
    if start_time is None and end_time is None:
        return
    if start_time is None or end_time is None:
        raise AbsenceServiceError("start_time y end_time deben venir juntos, o ninguno de los dos")
    if start_date != end_date:
        raise AbsenceServiceError("Un permiso parcial por horas debe ser de un solo día (start_date == end_date)")
    if end_time <= start_time:
        raise AbsenceServiceError("end_time debe ser mayor que start_time")


def initial_manager_status(has_manager: bool) -> str:
    """FR-011b: sin Jefe directo asignado, esa mitad de la aprobación nace ya resuelta."""
    return "approved" if not has_manager else "pending"


def overall_status(manager_status: str, hr_status: str) -> str:
    """Decisión 4: rejected si cualquiera de los dos lo es; approved solo si ambos lo son;
    pending en cualquier otro caso."""
    if manager_status == "rejected" or hr_status == "rejected":
        return "rejected"
    if manager_status == "approved" and hr_status == "approved":
        return "approved"
    return "pending"


def assert_not_own_request(decider_resource_id: uuid.UUID, request: AbsenceRequest) -> None:
    """FR-012: ni el Jefe directo ni RRHH pueden decidir sobre su propia solicitud."""
    if decider_resource_id == request.resource_id:
        raise AbsenceServiceError("No puedes decidir sobre tu propia solicitud", code="own_request")


def assert_can_decide(role: str, request: AbsenceRequest) -> None:
    """Bloquea una nueva decisión si ese lado ya fue decidido (idempotencia simple, sin reabrir)."""
    current = request.manager_status if role == "manager" else request.hr_status
    if current != "pending":
        raise AbsenceServiceError("Esta solicitud ya fue decidida por este rol", code="already_decided")


def assert_no_overlap(overlapping: list[AbsenceRequest], start_date: Optional[date] = None,
                      end_date: Optional[date] = None, start_time: Optional[time] = None,
                      end_time: Optional[time] = None) -> None:
    """FR-009 (edge case): no puede solaparse con otra solicitud propia vigente.

    FR-017 (spec 022): si la nueva solicitud y una existente son ambas parciales por horas del
    mismo día (`start_date == end_date` de ambos), solo hay conflicto real si además se solapan
    los rangos de horas — dos permisos de horas distintas el mismo día pueden coexistir. Si
    cualquiera de las dos es de día completo, el solape de fechas ya basta (comportamiento
    original, sin cambios)."""
    for existing in overlapping:
        both_same_day_partial = (
            start_time is not None and end_time is not None
            and start_date is not None and end_date is not None and start_date == end_date
            and existing.start_time is not None and existing.end_time is not None
            and existing.start_date == existing.end_date == start_date
        )
        if both_same_day_partial and (end_time <= existing.start_time or start_time >= existing.end_time):
            continue  # mismo día, pero rangos de horas disjuntos: no es un conflicto real
        raise AbsenceServiceError(
            "Ya existe una solicitud de ausencia que se solapa con estas fechas", code="overlap"
        )
