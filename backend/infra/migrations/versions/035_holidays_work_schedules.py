"""holidays + work_schedules (Fase 5 SDD V3, spec 020, research.md Decisiones 2/3/6)

Revision ID: 035
Revises: 034
Create Date: 2026-07-16

Ambas tablas quedan sin RLS — son datos de referencia no sensibles, mismo criterio que las
tablas `catalog_*` existentes (Decisión 6). Se incluye un seed de hasta 10 festivos de prueba
(Principio VII) para los países ya usados hoy por Clientes/Recursos (CO, MX), suficiente para
validar `quickstart.md` sin depender de un servicio externo.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None

_SEED_HOLIDAYS = [
    ("CO", "2026-01-01", "Año Nuevo"),
    ("CO", "2026-10-12", "Día de la Raza"),
    ("CO", "2026-12-25", "Navidad"),
    ("MX", "2026-01-01", "Año Nuevo"),
    ("MX", "2026-09-16", "Día de la Independencia"),
]


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "uq_holidays_country_date_name", "holidays", ["country", "holiday_date", "name"])

    op.create_table(
        "work_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "uq_work_schedules_resource_weekday", "work_schedules", ["resource_id", "weekday"])
    op.create_check_constraint(
        "ck_work_schedules_weekday", "work_schedules", "weekday BETWEEN 0 AND 6")
    op.create_check_constraint(
        "ck_work_schedules_time_order", "work_schedules", "end_time > start_time")

    bind = op.get_bind()
    for country, holiday_date, name in _SEED_HOLIDAYS:
        bind.execute(
            sa.text(
                "INSERT INTO holidays (id, country, holiday_date, name) "
                "VALUES (gen_random_uuid(), :country, :holiday_date, :name)"
            ),
            {"country": country, "holiday_date": holiday_date, "name": name},
        )


def downgrade() -> None:
    op.drop_table("work_schedules")
    op.drop_table("holidays")
