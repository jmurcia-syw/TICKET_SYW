"""create work_sessions + work_session_edits (Fase 2 — registro diario de tiempos)

Revision ID: 015
Revises: 014
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("duration_minutes > 0", name="ck_work_sessions_duration_positive"),
    )
    op.create_index("ix_work_sessions_resource_date", "work_sessions", ["resource_id", "work_date"])
    op.create_index("ix_work_sessions_ticket_id", "work_sessions", ["ticket_id"])

    op.create_table(
        "work_session_edits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("work_session_id", UUID(as_uuid=True), sa.ForeignKey("work_sessions.id"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("previous_values", JSONB(), nullable=True),
        sa.Column("new_values", JSONB(), nullable=True),
        sa.Column("edited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("edited_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("action IN ('created','updated','deleted')", name="ck_work_session_edits_action"),
    )
    op.create_index("ix_work_session_edits_session_id", "work_session_edits", ["work_session_id"])


def downgrade() -> None:
    op.drop_table("work_session_edits")
    op.drop_table("work_sessions")
