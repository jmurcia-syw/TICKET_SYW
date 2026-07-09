"""tasks: tickets.list_name + status CHECK ampliado con estados de Tarea (Fase 3, FR-009/FR-010)

Revision ID: 023
Revises: 022
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None

OLD_STATUSES = (
    "nuevo", "pre_analisis", "contacto", "en_analisis", "en_ejecucion",
    "en_pruebas", "pendiente_usuario", "resuelto", "cerrado", "cancelado",
)
NEW_STATUSES = OLD_STATUSES + ("pendiente", "en_progreso", "hecha")


def upgrade() -> None:
    op.add_column("tickets", sa.Column("list_name", sa.Text(), nullable=True))

    op.drop_constraint("ck_tickets_status", "tickets", type_="check")
    status_check = ", ".join(f"'{s}'" for s in NEW_STATUSES)
    op.create_check_constraint("ck_tickets_status", "tickets", f"status IN ({status_check})")


def downgrade() -> None:
    op.drop_constraint("ck_tickets_status", "tickets", type_="check")
    status_check = ", ".join(f"'{s}'" for s in OLD_STATUSES)
    op.create_check_constraint("ck_tickets_status", "tickets", f"status IN ({status_check})")

    op.drop_column("tickets", "list_name")
