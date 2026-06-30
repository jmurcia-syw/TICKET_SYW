"""create projects table

Revision ID: 003
Revises: 002
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date_estimated", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("client_id", "name", name="uq_projects_client_name"),
        sa.CheckConstraint("end_date_estimated IS NULL OR end_date_estimated >= start_date", name="ck_projects_dates"),
    )
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("projects")
