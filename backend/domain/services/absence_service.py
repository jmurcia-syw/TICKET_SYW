"""absence_service — dominio puro, sin DB (spec 020, Fase 5, Historia 2).

Reglas de la cadena de aprobación (Jefe directo + RRHH) — Decisión 4 de research.md.
Sin imports de Flask/SQLAlchemy (Principio I).
"""
from datetime import date
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


def assert_no_overlap(overlapping: list[AbsenceRequest]) -> None:
    """FR-009 (edge case): no puede solaparse con otra solicitud propia vigente."""
    if overlapping:
        raise AbsenceServiceError(
            "Ya existe una solicitud de ausencia que se solapa con estas fechas", code="overlap"
        )
