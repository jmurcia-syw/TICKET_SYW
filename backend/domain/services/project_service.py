from datetime import date
import uuid


class ProjectBusinessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ProjectService:
    def validate_create(self, client_id: uuid.UUID, name: str, start_date: date, end_date: date | None, clients_repo=None, projects_repo=None) -> None:
        if clients_repo:
            client = clients_repo.get_by_id(client_id)
            if client is None:
                raise ProjectBusinessError("client_not_found", "Cliente no encontrado")
            if not client.active:
                raise ProjectBusinessError("client_inactive", "No se puede crear un proyecto para un cliente inactivo")

        if end_date and end_date < start_date:
            raise ProjectBusinessError("invalid_dates", "La fecha de fin no puede ser anterior a la fecha de inicio")

        if projects_repo:
            existing = projects_repo.get_by_client_and_name(client_id, name)
            if existing:
                raise ProjectBusinessError("name_duplicate", "Ya existe un proyecto con ese nombre para este cliente")
