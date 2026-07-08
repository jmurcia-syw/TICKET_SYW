import uuid
from backend.domain.errors import DomainError


class ClientContactBusinessError(DomainError):
    pass


class ClientContactService:
    def validate_create(self, *, client_id: uuid.UUID, email: str, clients_repo, users_repo) -> None:
        client = clients_repo.get_by_id(client_id)
        if not client or not client.active:
            raise ClientContactBusinessError(
                "client_not_found", "Cliente no encontrado o inactivo", status_code=404)
        if users_repo.get_by_email(email):
            raise ClientContactBusinessError("email_in_use", "Ya existe un usuario con ese email")
