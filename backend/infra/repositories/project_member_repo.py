from typing import Optional
import uuid
from sqlalchemy.orm import Session
from backend.infra.models.project_member_model import (
    ProjectMemberModel, ProjectTeamModel, project_team_members_table,
)
from backend.infra.models.user_model import UserModel
from backend.infra.models.role_model import RoleModel
from backend.infra.models.resource_model import ResourceModel
from backend.domain.entities.project_member import ProjectMember, ProjectTeam


class ProjectMemberRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── members ──────────────────────────────────────────────────────────────

    def _member_row_to_dict(self, member: ProjectMemberModel, user: UserModel,
                            role_name: Optional[str], full_name: Optional[str]) -> dict:
        return {
            "id": str(member.id),
            "project_id": str(member.project_id),
            "user_id": str(member.user_id),
            "full_name": full_name or (user.username if user else None),
            "email": user.email if user else None,
            "role_name": role_name,
            "assigned_at": member.assigned_at.isoformat() if member.assigned_at else None,
        }

    def list_by_project(self, project_id: uuid.UUID,
                        role_name: Optional[str] = None) -> list[dict]:
        """Personal del proyecto con rol derivado del usuario (una sola fuente de verdad)
        y nombre del recurso vinculado si existe (fallback: username)."""
        q = (
            self._db.query(ProjectMemberModel, UserModel, RoleModel.name, ResourceModel.full_name)
            .join(UserModel, UserModel.id == ProjectMemberModel.user_id)
            .join(RoleModel, RoleModel.id == UserModel.role_id)
            .outerjoin(ResourceModel, ResourceModel.user_id == UserModel.id)
            .filter(ProjectMemberModel.project_id == project_id)
        )
        if role_name:
            q = q.filter(RoleModel.name == role_name)
        rows = q.order_by(ProjectMemberModel.assigned_at).all()
        return [self._member_row_to_dict(m, u, rn, fn) for m, u, rn, fn in rows]

    def get_by_id(self, member_id: uuid.UUID) -> Optional[ProjectMember]:
        model = self._db.get(ProjectMemberModel, member_id)
        return model.to_entity() if model else None

    def is_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return (
            self._db.query(ProjectMemberModel)
            .filter(ProjectMemberModel.project_id == project_id,
                    ProjectMemberModel.user_id == user_id)
            .first()
        ) is not None

    def get_by_project_and_user(self, project_id: uuid.UUID,
                                user_id: uuid.UUID) -> Optional[ProjectMember]:
        model = (
            self._db.query(ProjectMemberModel)
            .filter(ProjectMemberModel.project_id == project_id,
                    ProjectMemberModel.user_id == user_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_project_ids_by_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        rows = (
            self._db.query(ProjectMemberModel.project_id)
            .filter(ProjectMemberModel.user_id == user_id)
            .all()
        )
        return [r[0] for r in rows]

    def map_projects_by_user_ids(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict]]:
        """Proyectos vinculados por usuario, en una sola query (listado de Usuarios/cliente)."""
        if not user_ids:
            return {}
        from backend.infra.models.project_model import ProjectModel
        rows = (
            self._db.query(ProjectMemberModel.user_id, ProjectModel.id, ProjectModel.name)
            .join(ProjectModel, ProjectModel.id == ProjectMemberModel.project_id)
            .filter(ProjectMemberModel.user_id.in_(user_ids))
            .order_by(ProjectModel.name)
            .all()
        )
        result: dict[uuid.UUID, list[dict]] = {}
        for user_id, project_id, name in rows:
            result.setdefault(user_id, []).append({"id": str(project_id), "name": name})
        return result

    def create(self, member: ProjectMember) -> ProjectMember:
        model = ProjectMemberModel(id=member.id, project_id=member.project_id, user_id=member.user_id)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def delete(self, member_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        """Desasigna del proyecto; las filas de subgrupos caen por ON DELETE CASCADE."""
        model = self._db.get(ProjectMemberModel, member_id)
        if not model or model.project_id != project_id:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    # ── teams (subgrupos "Equipo") ───────────────────────────────────────────

    def get_team_by_id(self, team_id: uuid.UUID) -> Optional[ProjectTeam]:
        model = self._db.get(ProjectTeamModel, team_id)
        return model.to_entity() if model else None

    def get_team_by_name(self, project_id: uuid.UUID, name: str) -> Optional[ProjectTeam]:
        model = (
            self._db.query(ProjectTeamModel)
            .filter(ProjectTeamModel.project_id == project_id, ProjectTeamModel.name == name)
            .first()
        )
        return model.to_entity() if model else None

    def list_teams(self, project_id: uuid.UUID) -> list[dict]:
        """Subgrupos del proyecto con sus miembros resueltos (nombre/correo/rol)."""
        teams = (
            self._db.query(ProjectTeamModel)
            .filter(ProjectTeamModel.project_id == project_id)
            .order_by(ProjectTeamModel.created_at)
            .all()
        )
        result = []
        for team in teams:
            member_rows = (
                self._db.query(ProjectMemberModel, UserModel, RoleModel.name, ResourceModel.full_name)
                .join(project_team_members_table,
                      project_team_members_table.c.member_id == ProjectMemberModel.id)
                .join(UserModel, UserModel.id == ProjectMemberModel.user_id)
                .join(RoleModel, RoleModel.id == UserModel.role_id)
                .outerjoin(ResourceModel, ResourceModel.user_id == UserModel.id)
                .filter(project_team_members_table.c.team_id == team.id)
                .order_by(ProjectMemberModel.assigned_at)
                .all()
            )
            members = [
                {
                    "member_id": str(m.id),
                    "user_id": str(m.user_id),
                    "full_name": fn or (u.username if u else None),
                    "email": u.email if u else None,
                    "role_name": rn,
                }
                for m, u, rn, fn in member_rows
            ]
            result.append({
                "id": str(team.id),
                "project_id": str(team.project_id),
                "name": team.name,
                "members": members,
                "member_count": len(members),
                "created_at": team.created_at.isoformat() if team.created_at else None,
            })
        return result

    def create_team(self, team: ProjectTeam) -> ProjectTeam:
        model = ProjectTeamModel(id=team.id, project_id=team.project_id, name=team.name)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def rename_team(self, team_id: uuid.UUID, name: str) -> Optional[ProjectTeam]:
        model = self._db.get(ProjectTeamModel, team_id)
        if not model:
            return None
        model.name = name
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def delete_team(self, team_id: uuid.UUID) -> bool:
        """Borra el subgrupo; sus miembros siguen asignados al proyecto (cascade solo
        elimina las filas de project_team_members)."""
        model = self._db.get(ProjectTeamModel, team_id)
        if not model:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    def replace_team_members(self, team_id: uuid.UUID, member_ids: list[uuid.UUID]) -> None:
        """Patrón "lista completa" (igual que resource_skills): reemplaza el conjunto."""
        self._db.execute(
            project_team_members_table.delete().where(
                project_team_members_table.c.team_id == team_id)
        )
        for member_id in member_ids:
            self._db.execute(
                project_team_members_table.insert().values(team_id=team_id, member_id=member_id)
            )
        self._db.commit()
