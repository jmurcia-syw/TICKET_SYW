"""permiso work_hour_templates:manage para roles RRHH y Admin (spec 022, FR-001)

Revision ID: 044
Revises: 043
Create Date: 2026-07-17

Mismo patrón que 039_rrhh_role_permissions.py.
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = {
    ("work_hour_templates", "manage"): ["Admin", "RRHH"],
}


def upgrade() -> None:
    bind = op.get_bind()
    roles = {r.name: r.id for r in bind.execute(sa.text("SELECT id, name FROM roles")).fetchall()}

    for (module, action), role_names in NEW_PERMISSIONS.items():
        perm_id = uuid.uuid4()
        bind.execute(
            sa.text("INSERT INTO permissions (id, module, action) VALUES (:id, :module, :action)"),
            {"id": str(perm_id), "module": module, "action": action},
        )
        for role_name in role_names:
            if role_name in roles:
                bind.execute(
                    sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                    {"r": str(roles[role_name]), "p": str(perm_id)},
                )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE module = 'work_hour_templates')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'work_hour_templates'"))
