"""work_hour_template_service — dominio puro, sin DB (spec 022, Historia 1).

Valida los datos de una Franja Horaria global (timezone IANA, orden de horas por slot) antes
de que la ruta la persista vía `WorkHourTemplateRepository` (Capa 2, `calendar_repo.py`) —
mismo patrón que `absence_service.py` (Principio I: sin imports de Flask/SQLAlchemy). La
persistencia y la propagación a los recursos heredados NO viven aquí (research.md Decisión 12).
"""
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class WorkHourTemplateServiceError(Exception):
    def __init__(self, message: str, code: str = "validation_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def validate_timezone(timezone: str) -> None:
    """FR-001: el huso horario debe ser una zona IANA válida (ej. `America/Bogota`)."""
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        raise WorkHourTemplateServiceError(f"'{timezone}' no es una zona horaria IANA válida")


def validate_slots(slots: list[dict]) -> None:
    """FR-002: cada slot debe tener `weekday` en 0-6, `end_time > start_time`, y no repetir
    `weekday` (mismo criterio que `WorkScheduleSlot`, spec 020)."""
    seen_weekdays: set[int] = set()
    for slot in slots:
        weekday = slot.get("weekday")
        start_time = slot.get("start_time")
        end_time = slot.get("end_time")
        if not isinstance(weekday, int) or weekday < 0 or weekday > 6:
            raise WorkHourTemplateServiceError("weekday debe ser un entero entre 0 y 6")
        if weekday in seen_weekdays:
            raise WorkHourTemplateServiceError(f"weekday {weekday} repetido")
        if not isinstance(start_time, time) or not isinstance(end_time, time) or end_time <= start_time:
            raise WorkHourTemplateServiceError(
                "start_time/end_time inválidos (end_time debe ser mayor que start_time)"
            )
        seen_weekdays.add(weekday)
