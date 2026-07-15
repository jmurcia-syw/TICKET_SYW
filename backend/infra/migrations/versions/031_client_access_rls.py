"""enable RLS on client_access and client_access_attachments (spec 018, research.md Decisión 5)

Revision ID: 031
Revises: 030
Create Date: 2026-07-15
"""
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None

# Mismo patron app-level que 012_tickets_rls.py/016_work_sessions_rls.py/020_client_contacts_rls.py:
# red de seguridad de la capa de datos. `client_access` guarda credenciales — Principio IV
# (NON-NEGOTIABLE) exige RLS en toda tabla con datos sensibles.
TABLES = ("client_access", "client_access_attachments")


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
