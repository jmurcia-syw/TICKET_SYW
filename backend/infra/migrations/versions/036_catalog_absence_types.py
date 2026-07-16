"""catalog_absence_types: tipos de solicitud de ausencia (Fase 5 SDD V3, spec 020)

Revision ID: 036
Revises: 035
Create Date: 2026-07-16
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None

ABSENCE_TYPE_SEEDS = ["Vacaciones", "Incapacidad médica", "Permiso personal", "Otro"]


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "catalog_absence_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    for name in ABSENCE_TYPE_SEEDS:
        bind.execute(
            sa.text("INSERT INTO catalog_absence_types (id, name) VALUES (:id, :name)"),
            {"id": str(uuid.uuid4()), "name": name},
        )


def downgrade() -> None:
    op.drop_table("catalog_absence_types")
