"""enable RLS on work_sessions tables (research.md Decision 4 — doble proteccion Principio IV)

Revision ID: 016
Revises: 015
Create Date: 2026-07-07
"""
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

# Mismo patron que 012_tickets_rls.py: RLS como red de seguridad de la capa de datos.
# La restriccion real "un recurso ve solo lo suyo, Coordinador/QM/Admin ven todo" se aplica
# en dominio+API (work_sessions:view_own vs work_sessions:view_all), no aqui.
TABLES = ("work_sessions", "work_session_edits")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_app_access ON {table} "
            f"USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' "
            f"OR current_user = 'sywork_user')"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_app_access ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
