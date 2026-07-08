"""enable RLS on client_contacts (research.md Decision 2 — doble proteccion Principio IV)

Revision ID: 020
Revises: 019
Create Date: 2026-07-08
"""
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

# Mismo patron app-level que 012_tickets_rls.py/016_work_sessions_rls.py: red de seguridad de
# la capa de datos. La restriccion real ("un Encargado solo ve su propia fila") no aplica aqui
# porque el dominio resuelve client_id desde el user_id autenticado, nunca desde un parametro.
TABLE = "client_contacts"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {TABLE}_app_access ON {TABLE} "
        f"USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' "
        f"OR current_user = 'sywork_user')"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_app_access ON {TABLE}")
    op.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")
