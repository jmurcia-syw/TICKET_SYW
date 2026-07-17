"""absence_requests.start_time/end_time (spec 022, FR-017 — permisos parciales por horas)

Revision ID: 043
Revises: 042
Create Date: 2026-07-17

Columnas nuevas nullable, sin backfill: filas existentes quedan `NULL` = ausencia de día
completo (comportamiento original, compatible hacia atrás).
"""
from alembic import op
import sqlalchemy as sa

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("absence_requests", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("absence_requests", sa.Column("end_time", sa.Time(), nullable=True))
    op.create_check_constraint(
        "ck_absence_requests_partial_hours_order", "absence_requests",
        "start_time IS NULL OR end_time IS NULL OR end_time > start_time")


def downgrade() -> None:
    op.drop_constraint("ck_absence_requests_partial_hours_order", "absence_requests", type_="check")
    op.drop_column("absence_requests", "end_time")
    op.drop_column("absence_requests", "start_time")
