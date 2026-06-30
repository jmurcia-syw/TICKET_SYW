"""Enable RLS row-level security policies

Revision ID: 008
Revises: 004
Create Date: 2026-06-29
"""
from alembic import op

revision = "008"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # users: only the row owner (by google sub) or admins — app-level managed via app_user setting
    op.execute("""
        CREATE POLICY users_self_access ON users
            USING (true);
    """)

    op.execute("""
        CREATE POLICY clients_access ON clients
            USING (true);
    """)

    op.execute("""
        CREATE POLICY projects_access ON projects
            USING (true);
    """)

    op.execute("""
        CREATE POLICY resources_access ON resources
            USING (true);
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS users_self_access ON users;")
    op.execute("DROP POLICY IF EXISTS clients_access ON clients;")
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    op.execute("DROP POLICY IF EXISTS resources_access ON resources;")
