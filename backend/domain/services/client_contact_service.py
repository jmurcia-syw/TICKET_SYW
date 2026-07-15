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

    def resolve_common_client(self, project_ids: list[uuid.UUID], projects_repo) -> uuid.UUID:
        """Resuelve una lista de Proyectos y valida que compartan un único Cliente (spec 015).

        Un Usuario/cliente pertenece a un único Cliente; sus Proyectos deben ser todos de ese
        Cliente, nunca de Clientes distintos.
        """
        client_ids: set[uuid.UUID] = set()
        for project_id in project_ids:
            project = projects_repo.get_by_id(project_id)
            if not project:
                raise ClientContactBusinessError(
                    "not_found", "Proyecto no encontrado", status_code=404)
            if not project.active:
                raise ClientContactBusinessError(
                    "project_inactive", "El proyecto está inactivo", status_code=409)
            client_ids.add(project.client_id)
        if len(client_ids) > 1:
            raise ClientContactBusinessError(
                "validation_error",
                "Los proyectos seleccionados deben pertenecer todos al mismo Cliente",
                status_code=400)
        return next(iter(client_ids))
