from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

# Tipos de comentario estructurados (FR-013). Nunca texto libre.
COMMENT_TYPES = (
    "asignado", "pre_analisis", "confirmacion_atencion", "solicitud_informacion",
    "termina_analisis", "solicitud_cierre", "respuesta_usuario",
    "descripcion_solucion", "comentario_interno", "cancelacion",
)

# Visibilidad por tipo (FR-016): external = visible al cliente (Portal, Fase 8)
COMMENT_VISIBILITY = {
    "asignado": "internal",
    "pre_analisis": "internal",
    "confirmacion_atencion": "external",
    "solicitud_informacion": "external",
    "termina_analisis": "internal",
    "solicitud_cierre": "external",
    "respuesta_usuario": "external",
    "descripcion_solucion": "internal",
    "comentario_interno": "internal",
    "cancelacion": "internal",
}

COMMENT_TYPE_LABELS = {
    "asignado": "Asignado",
    "pre_analisis": "Pre-Análisis",
    "confirmacion_atencion": "Confirmación de atención",
    "solicitud_informacion": "Solicitud de información",
    "termina_analisis": "Termina análisis",
    "solicitud_cierre": "Solicitud de cierre",
    "respuesta_usuario": "Respuesta de usuario",
    "descripcion_solucion": "Descripción solución",
    "comentario_interno": "Comentario interno",
    "cancelacion": "Cancelación",
}


@dataclass
class Attachment:
    id: uuid.UUID
    comment_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Comment:
    id: uuid.UUID
    ticket_id: uuid.UUID
    comment_type: str
    body: str
    author_id: uuid.UUID
    visibility: str = "internal"
    is_automatic: bool = False
    attachments: list[Attachment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, ticket_id: uuid.UUID, comment_type: str, body: str,
               author_id: uuid.UUID, is_automatic: bool = False) -> "Comment":
        return cls(
            id=uuid.uuid4(),
            ticket_id=ticket_id,
            comment_type=comment_type,
            body=body,
            author_id=author_id,
            visibility=COMMENT_VISIBILITY.get(comment_type, "internal"),
            is_automatic=is_automatic,
        )
