"""catalog_resolution_types.allow_zero_time — permite cerrar sin tiempo registrado (OBS-0026)

Revision ID: 033
Revises: 032
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None

# Tipos de resolución existentes que semánticamente no implican trabajo de resolución
# (cierre por descarte o por inacción del usuario, no por una solución entregada).
ALLOW_ZERO_TIME_NAMES = ["No es incidente", "Sin respuesta de usuario"]


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column(
        "catalog_resolution_types",
        sa.Column("allow_zero_time", sa.Boolean(), nullable=False, server_default="false"),
    )
    bind.execute(
        sa.text("UPDATE catalog_resolution_types SET allow_zero_time = true WHERE name = ANY(:names)"),
        {"names": ALLOW_ZERO_TIME_NAMES},
    )


def downgrade() -> None:
    op.drop_column("catalog_resolution_types", "allow_zero_time")
