"""Reglas de negocio del Personal del Proyecto y sus subgrupos "Equipo" (spec 010).

Capa 1 pura: sin imports de Flask/SQLAlchemy — los repos llegan por parámetro.
"""
import uuid

from backend.domain.errors import DomainError


class ProjectMemberBusinessError(DomainError):
    pass


class ProjectMemberService:
    def validate_assign(self, project_id: uuid.UUID, user_id: uuid.UUID,
                        users_repo, members_repo) -> None:
        user = users_repo.get_by_id(user_id)
        if not user:
            raise ProjectMemberBusinessError("not_found", "Usuario no encontrado", status_code=404)
        if not user.active:
            raise ProjectMemberBusinessError("user_inactive", "El usuario está desactivado")
        if members_repo.is_member(project_id, user_id):
            raise ProjectMemberBusinessError(
                "already_member", "La persona ya está asignada a este proyecto")

    def validate_team_name(self, project_id: uuid.UUID, name: str, members_repo,
                           exclude_team_id: uuid.UUID | None = None) -> str:
        clean = (name or "").strip()
        if not clean:
            raise ProjectMemberBusinessError(
                "validation_error", "El nombre del equipo es requerido", status_code=400)
        existing = members_repo.get_team_by_name(project_id, clean)
        if existing and existing.id != exclude_team_id:
            raise ProjectMemberBusinessError(
                "duplicate_name", "Ya existe un equipo con ese nombre en el proyecto")
        return clean

    def validate_team_members(self, project_id: uuid.UUID,
                              member_ids: list[uuid.UUID], members_repo) -> None:
        for member_id in member_ids:
            member = members_repo.get_by_id(member_id)
            if not member or member.project_id != project_id:
                raise ProjectMemberBusinessError(
                    "member_not_in_project",
                    "Todos los miembros del equipo deben ser personal asignado del proyecto",
                    member_id=str(member_id))
