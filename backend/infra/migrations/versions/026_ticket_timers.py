"""cronómetro manual de tiempo por recurso (provisional)

Revision ID: 026
Revises: 025
Create Date: 2026-07-09

Spec 012 — tabla nueva `ticket_timers`, una fila por recurso (PK `resource_id`, data-model.md
Decisión 1): guarda el estado del cronómetro (inactivo|en curso|pausado), el ticket asociado
mientras está activo, y los timestamps necesarios para derivar el tiempo transcurrido sin
depender de ningún proceso en segundo plano (research.md Decisión 2). No modifica ninguna tabla
existente.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None

CONSISTENCY_CHECK = (
    "(status = 'inactive' AND ticket_id IS NULL AND started_at IS NULL) OR "
    "(status = 'paused' AND ticket_id IS NOT NULL AND started_at IS NULL) OR "
    "(status = 'running' AND ticket_id IS NOT NULL AND started_at IS NOT NULL)"
)


def upgrade() -> None:
    op.create_table(
        "ticket_timers",
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="inactive"),
        sa.Column("accumulated_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_check_constraint(
        "ck_ticket_timers_status", "ticket_timers", "status IN ('inactive','running','paused')")
    op.create_check_constraint(
        "ck_ticket_timers_consistency", "ticket_timers", CONSISTENCY_CHECK)

    # RLS app-level, mismo patrón que 025_project_members_skills.py — el aislamiento real por
    # resource_id (FR-005) se aplica en la capa API, no en Postgres.
    op.execute("ALTER TABLE ticket_timers ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY ticket_timers_app_access ON ticket_timers "
        "USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' "
        "OR current_user = 'sywork_user')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS ticket_timers_app_access ON ticket_timers")
    op.drop_table("ticket_timers")
