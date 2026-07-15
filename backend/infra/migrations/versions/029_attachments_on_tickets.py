"""Adjuntos también en la descripción del Ticket/Tarea (spec 017)

Revision ID: 029
Revises: 028
Create Date: 2026-07-14

`comment_attachments.comment_id` deja de ser obligatorio y se agrega `ticket_id` (nullable,
FK `tickets`), con un CHECK que exige exactamente uno de los dos: un adjunto es de un Comentario
o de la descripción de un Ticket/Tarea, nunca de ambos ni de ninguno (data-model.md, spec 017).
Sin renombrar la tabla (minimizar el diff, research.md Decisión 4).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("comment_attachments", "comment_id", nullable=True)
    op.add_column("comment_attachments", sa.Column(
        "ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=True))
    op.create_index("ix_comment_attachments_ticket_id", "comment_attachments", ["ticket_id"])
    op.create_check_constraint(
        "ck_attachment_exactly_one_parent", "comment_attachments",
        "(comment_id IS NOT NULL) <> (ticket_id IS NOT NULL)")


def downgrade() -> None:
    op.drop_constraint("ck_attachment_exactly_one_parent", "comment_attachments", type_="check")
    op.drop_index("ix_comment_attachments_ticket_id", table_name="comment_attachments")
    op.drop_column("comment_attachments", "ticket_id")
    op.alter_column("comment_attachments", "comment_id", nullable=False)
