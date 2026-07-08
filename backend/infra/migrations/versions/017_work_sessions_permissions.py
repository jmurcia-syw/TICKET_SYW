"""seed permission catalog for work_sessions module (Fase 2)

Revision ID: 017
Revises: 016
Create Date: 2026-07-07
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

# module -> (action, [role names])
PERMISSION_MATRIX = {
    ("work_sessions", "view_own"): ["Admin", "Coordinador", "QM", "Resolutor"],
    ("work_sessions", "manage"): ["Admin", "Coordinador", "QM", "Resolutor"],
    ("work_sessions", "view_all"): ["Admin", "Coordinador", "QM"],
    ("work_sessions", "manage_all"): ["Admin"],
}


def upgrade() -> None:
    bind = op.get_bind()
    roles = {r.name: r.id for r in bind.execute(sa.text("SELECT id, name FROM roles")).fetchall()}
    for (module, action), role_names in PERMISSION_MATRIX.items():
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
        "(SELECT id FROM permissions WHERE module = 'work_sessions')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'work_sessions'"))
