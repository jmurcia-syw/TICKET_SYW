"""create ticket_reassignments (spec 023, reasignación de resolutor) + RLS

Revision ID: 045
Revises: 044
Create Date: 2026-07-21

Tabla append-only análoga a `ticket_assignments` (011_create_tickets.py), pero separada para no
mezclar la reasignación con el Gold Standard Dataset de la asignación inicial (research.md
Decisión 4). Misma política de RLS que las demás tablas de tickets (012_tickets_rls.py).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_reassignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_assignee_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=True),
        sa.Column("new_assignee_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reassignments_ticket_id", "ticket_reassignments", ["ticket_id"])

    op.execute("ALTER TABLE ticket_reassignments ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY ticket_reassignments_app_access ON ticket_reassignments "
        "USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' "
        "OR current_user = 'sywork_user')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS ticket_reassignments_app_access ON ticket_reassignments")
    op.execute("ALTER TABLE ticket_reassignments DISABLE ROW LEVEL SECURITY")
    op.drop_table("ticket_reassignments")
