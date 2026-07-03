"""enable RLS on tickets tables (Decision 9, research.md — doble proteccion Principio IV)

Revision ID: 012
Revises: 011
Create Date: 2026-07-02
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

# Lectura para cualquier sesion autenticada de la aplicacion (los resolutores usan el
# historial de tickets como base de conocimiento — SDD V3 "Concepto de Skills").
# La restriccion de ESCRITURA/transicion (solo asignado o Coordinador/QM/Admin) se aplica
# en dominio+API (FR-028); RLS aqui es la red de seguridad de la capa de datos.
TABLES = ("tickets", "ticket_comments", "comment_attachments",
          "ticket_status_transitions", "ticket_assignments")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # la app se conecta con el owner: FORCE aplica RLS tambien al owner
        op.execute(
            f"CREATE POLICY {table}_app_access ON {table} "
            f"USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' "
            f"OR current_user = 'sywork_user')"
        )
    # notifications: cada usuario solo las suyas (defensa extra a nivel de datos)
    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY notifications_owner ON notifications "
        "USING (current_setting('app.user_id', true) IS NULL "
        "OR user_id::text = current_setting('app.user_id', true))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS notifications_owner ON notifications")
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY")
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_app_access ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
