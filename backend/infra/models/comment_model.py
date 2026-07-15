import uuid
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.comment import Comment, Attachment


class CommentModel(Base):
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    comment_type = Column(Text, nullable=False)
    visibility = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_automatic = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    attachments = relationship("AttachmentModel", lazy="joined")

    def to_entity(self) -> Comment:
        return Comment(
            id=self.id,
            ticket_id=self.ticket_id,
            comment_type=self.comment_type,
            visibility=self.visibility,
            body=self.body,
            author_id=self.author_id,
            is_automatic=self.is_automatic,
            attachments=[a.to_entity() for a in (self.attachments or [])],
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, comment: Comment) -> "CommentModel":
        return cls(
            id=comment.id,
            ticket_id=comment.ticket_id,
            comment_type=comment.comment_type,
            visibility=comment.visibility,
            body=comment.body,
            author_id=comment.author_id,
            is_automatic=comment.is_automatic,
        )


class AttachmentModel(Base):
    __tablename__ = "comment_attachments"
    __table_args__ = (
        CheckConstraint(
            "(comment_id IS NOT NULL) <> (ticket_id IS NOT NULL)",
            name="ck_attachment_exactly_one_parent",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    comment_id = Column(UUID(as_uuid=True), ForeignKey("ticket_comments.id"), nullable=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    filename = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,
            comment_id=self.comment_id,
            ticket_id=self.ticket_id,
            filename=self.filename,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            storage_path=self.storage_path,
            created_at=self.created_at,
        )
