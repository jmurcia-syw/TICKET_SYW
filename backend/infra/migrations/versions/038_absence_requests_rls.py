"""enable RLS on absence_requests and absence_request_attachments (spec 020, research.md Decisión 6)

Revision ID: 038
Revises: 037
Create Date: 2026-07-16
"""
from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None

# Mismo patron app-level que 012_tickets_rls.py/016_work_sessions_rls.py/031_client_access_rls.py:
# red de seguridad de la capa de datos. `absence_requests` puede contener información de salud
# (ej. tipo "Incapacidad médica") — Principio IV (NON-NEGOTIABLE) exige RLS en toda tabla con
# datos sensibles.
TABLES = ("absence_requests", "absence_request_attachments")


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
