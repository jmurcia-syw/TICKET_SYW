"""catalog_teams: catálogo administrable para el campo "Equipo" del perfil de Recursos (OBS-0024)

Revision ID: 032
Revises: 031
Create Date: 2026-07-15
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None

TEAM_SEEDS = ["Oracle EBS", "Oracle Fusion", "Data & Analytics", "Infraestructura", "Otro"]


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "catalog_teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    for name in TEAM_SEEDS:
        bind.execute(
            sa.text("INSERT INTO catalog_teams (id, name) VALUES (:id, :name)"),
            {"id": str(uuid.uuid4()), "name": name},
        )


def downgrade() -> None:
    op.drop_table("catalog_teams")
