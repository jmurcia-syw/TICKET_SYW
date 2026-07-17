"""resources.schedule_mode + work_hour_template_id (spec 022, research.md Decisiones 2/3)

Revision ID: 042
Revises: 041
Create Date: 2026-07-17

Migración de datos (research.md Decisión 3, confirmada con el usuario durante
`/speckit-specify`): todo recurso que ya tenga al menos una fila propia en `work_schedules`
queda marcado `schedule_mode = 'personalizado'` (conserva su horario actual sin cambios,
excluido de futuras Franjas globales); el resto nace `heredado` sin plantilla asignada
(cae al default hardcodeado L-V 08:00-17:00 de `availability_service`, comportamiento
idéntico al actual, hasta que RRHH le asigne una Franja Horaria de país).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column("schedule_mode", sa.Text(), nullable=False, server_default="heredado"),
    )
    op.add_column(
        "resources",
        sa.Column("work_hour_template_id", UUID(as_uuid=True),
                  sa.ForeignKey("work_hour_templates.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_check_constraint(
        "ck_resources_schedule_mode", "resources",
        "schedule_mode IN ('heredado', 'personalizado')")

    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE resources SET schedule_mode = 'personalizado' "
        "WHERE id IN (SELECT DISTINCT resource_id FROM work_schedules)"
    ))


def downgrade() -> None:
    op.drop_constraint("ck_resources_schedule_mode", "resources", type_="check")
    op.drop_column("resources", "work_hour_template_id")
    op.drop_column("resources", "schedule_mode")
