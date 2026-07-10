from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ProjectMember:
    """Vínculo persona ↔ Proyecto (spec 010): válido para cualquier usuario del sistema.
    El rol/tipo NO se almacena aquí — se deriva del rol del usuario al listar."""
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    assigned_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, project_id: uuid.UUID, user_id: uuid.UUID) -> "ProjectMember":
        return cls(id=uuid.uuid4(), project_id=project_id, user_id=user_id)


@dataclass
class ProjectTeam:
    """Subgrupo "Equipo" dentro de un Proyecto: agrupación visual de personal ya asignado.
    Eliminarlo no desasigna a sus miembros del Proyecto."""
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, project_id: uuid.UUID, name: str) -> "ProjectTeam":
        return cls(id=uuid.uuid4(), project_id=project_id, name=name)
