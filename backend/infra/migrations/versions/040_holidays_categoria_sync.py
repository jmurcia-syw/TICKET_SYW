"""holidays.category/source + holiday_sync_status (spec 021, research.md Decisiones 3/8)

Revision ID: 040
Revises: 039
Create Date: 2026-07-16

`category` distingue festivos "oficial" (nacional, normalmente sincronizado desde la API
externa) de "regional_religioso" (celebración local/religiosa, no afecta disponibilidad — FR-007).
`source` distingue si la fila vino de la sincronización automática ("api") o fue creada/editada
a mano ("manual") — una fila "manual" nunca es sobrescrita por la sincronización (FR-009).
Los festivos ya sembrados en spec 020 quedan con los defaults ("oficial"/"manual"), que son
correctos: son festivos nacionales reales cargados a mano en esa fase.

`holiday_sync_status` es una tabla operativa (sin RLS, Decisión 8) que registra el último
intento de sincronización por país/año, usada para decidir cuándo reintentar.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "holidays",
        sa.Column("category", sa.Text(), nullable=False, server_default="oficial"),
    )
    op.add_column(
        "holidays",
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
    )
    op.create_check_constraint(
        "ck_holidays_category", "holidays", "category IN ('oficial', 'regional_religioso')")
    op.create_check_constraint(
        "ck_holidays_source", "holidays", "source IN ('api', 'manual')")

    op.create_table(
        "holiday_sync_status",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("last_synced_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_holiday_sync_status_country_year", "holiday_sync_status", ["country", "year"])


def downgrade() -> None:
    op.drop_table("holiday_sync_status")
    op.drop_constraint("ck_holidays_source", "holidays", type_="check")
    op.drop_constraint("ck_holidays_category", "holidays", type_="check")
    op.drop_column("holidays", "source")
    op.drop_column("holidays", "category")
