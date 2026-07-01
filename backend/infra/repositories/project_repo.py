from typing import Optional
from sqlalchemy.orm import Session
from backend.infra.models.project_model import ProjectModel
from backend.domain.entities.project import Project
import uuid


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        model = self._db.get(ProjectModel, project_id)
        return model.to_entity() if model else None

    def get_by_client_and_name(self, client_id: uuid.UUID, name: str) -> Optional[Project]:
        model = self._db.query(ProjectModel).filter(
            ProjectModel.client_id == client_id,
            ProjectModel.name == name,
        ).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, client_id: uuid.UUID | None = None, search: str | None = None, active: bool | None = None) -> tuple[list[Project], int]:
        q = self._db.query(ProjectModel)
        if client_id:
            q = q.filter(ProjectModel.client_id == client_id)
        if search:
            q = q.filter(ProjectModel.name.ilike(f"%{search}%"))
        if active is not None:
            q = q.filter(ProjectModel.active == active)
        total = q.count()
        models = q.order_by(ProjectModel.name).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, project: Project) -> Project:
        model = ProjectModel.from_entity(project)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update(self, project: Project) -> Project:
        model = self._db.get(ProjectModel, project.id)
        if not model:
            return project
        for f in ("name", "description", "active", "start_date", "end_date_estimated"):
            setattr(model, f, getattr(project, f))
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def deactivate(self, project_id: uuid.UUID) -> Optional[Project]:
        return self.set_active(project_id, False)

    def set_active(self, project_id: uuid.UUID, active: bool) -> Optional[Project]:
        model = self._db.get(ProjectModel, project_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()
