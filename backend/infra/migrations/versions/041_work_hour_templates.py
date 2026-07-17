"""work_hour_templates + work_hour_template_slots (spec 022, Franja Horaria global por país)

Revision ID: 041
Revises: 040
Create Date: 2026-07-17

Plantilla global por país que un `Resource` con `schedule_mode == "heredado"` sigue
automáticamente en tiempo de lectura (join, no copia de filas) — mismo shape que
`work_schedules` (data-model.md).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_hour_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "work_hour_template_slots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", UUID(as_uuid=True),
                  sa.ForeignKey("work_hour_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_work_hour_template_slots_template_weekday", "work_hour_template_slots",
        ["template_id", "weekday"])
    op.create_check_constraint(
        "ck_work_hour_template_slots_weekday", "work_hour_template_slots", "weekday BETWEEN 0 AND 6")
    op.create_check_constraint(
        "ck_work_hour_template_slots_time_order", "work_hour_template_slots", "end_time > start_time")


def downgrade() -> None:
    op.drop_table("work_hour_template_slots")
    op.drop_table("work_hour_templates")
