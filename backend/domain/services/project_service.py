import unicodedata
from datetime import date
import uuid

from backend.domain.errors import DomainError


class ProjectBusinessError(DomainError):
    pass


_MAX_PROJECT_NAME_LENGTH = 150
# OBS-0010: caracteres especiales explícitamente rechazados (además de emojis, vía categoría
# Unicode "So" — Symbol/other, donde caen la mayoría de los emoji).
_DISALLOWED_NAME_CHARS = set("!@#$%^&*+={}[]|\\<>~`")


class ProjectService:
    def validate_name(self, name: str) -> None:
        """OBS-0010: longitud máxima y caracteres especiales/emojis no permitidos."""
        if len(name) > _MAX_PROJECT_NAME_LENGTH:
            raise ProjectBusinessError(
                "validation_error",
                f"El nombre del proyecto no puede superar {_MAX_PROJECT_NAME_LENGTH} caracteres",
                status_code=400)
        for ch in name:
            if ch in _DISALLOWED_NAME_CHARS or unicodedata.category(ch) == "So":
                raise ProjectBusinessError(
                    "validation_error", "El nombre del proyecto contiene caracteres no permitidos",
                    status_code=400)

    def validate_dates(self, start_date: date, end_date: date | None) -> None:
        """OBS-0011: la fecha de fin debe ser estrictamente posterior a la de inicio."""
        if end_date and end_date <= start_date:
            raise ProjectBusinessError(
                "invalid_dates", "La fecha de fin debe ser posterior a la fecha de inicio", status_code=400)

    def validate_start_date(self, start_date: date) -> None:
        """OBS-0011: al CREAR un proyecto, la fecha de inicio no puede quedar en un mes anterior
        al actual. Se aplica solo en creación (no en edición) para no bloquear proyectos ya
        cargados retroactivamente cuyo inicio real es anterior al alta en el sistema."""
        today = date.today()
        if (start_date.year, start_date.month) < (today.year, today.month):
            raise ProjectBusinessError(
                "invalid_start_date",
                "La fecha de inicio no puede estar en un mes anterior al actual",
                status_code=400)

    def validate_create(self, client_id: uuid.UUID, name: str, start_date: date, end_date: date | None,
                        clients_repo=None, projects_repo=None) -> None:
        if clients_repo:
            client = clients_repo.get_by_id(client_id)
            if client is None:
                raise ProjectBusinessError("client_not_found", "Cliente no encontrado", status_code=404)
            if not client.active:
                raise ProjectBusinessError("client_inactive", "No se puede crear un proyecto para un cliente inactivo")

        self.validate_name(name)
        self.validate_start_date(start_date)
        self.validate_dates(start_date, end_date)

        if projects_repo:
            existing = projects_repo.get_by_client_and_name(client_id, name)
            if existing:
                raise ProjectBusinessError("name_duplicate", "Ya existe un proyecto con ese nombre para este cliente")
