from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend.domain.entities.comment import Comment, Attachment
from backend.infra.models.comment_model import CommentModel, AttachmentModel


class CommentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, comment_id: uuid.UUID) -> Optional[Comment]:
        model = self._db.get(CommentModel, comment_id)
        return model.to_entity() if model else None

    def list_for_ticket(self, ticket_id: uuid.UUID) -> list[Comment]:
        models = (self._db.query(CommentModel)
                  .filter(CommentModel.ticket_id == ticket_id)
                  .order_by(CommentModel.created_at).all())
        return [m.to_entity() for m in models]

    def add(self, comment: Comment, commit: bool = True) -> Comment:
        model = CommentModel.from_entity(comment)
        self._db.add(model)
        if commit:
            self._db.commit()
            self._db.refresh(model)
            return model.to_entity()
        return comment

    def add_attachment(self, attachment: Attachment, commit: bool = True) -> None:
        self._db.add(AttachmentModel(
            id=attachment.id,
            comment_id=attachment.comment_id,
            ticket_id=attachment.ticket_id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=attachment.size_bytes,
            storage_path=attachment.storage_path,
        ))
        if commit:
            self._db.commit()

    def get_attachment(self, attachment_id: uuid.UUID) -> Optional[Attachment]:
        model = self._db.get(AttachmentModel, attachment_id)
        return model.to_entity() if model else None

    def list_ticket_attachments(self, ticket_id: uuid.UUID) -> list[Attachment]:
        """Adjuntos de la descripción de un Ticket/Tarea (spec 017) — independientes de los
        adjuntos de sus comentarios."""
        models = (self._db.query(AttachmentModel)
                  .filter(AttachmentModel.ticket_id == ticket_id)
                  .order_by(AttachmentModel.created_at).all())
        return [m.to_entity() for m in models]

    def commit(self) -> None:
        self._db.commit()
