"""seed rol RRHH + permisos absence_requests:create/view_all/decide_hr, holidays:manage
(Fase 5 SDD V3, spec 020, data-model.md "Rol y permisos nuevos")

Revision ID: 039
Revises: 038
Create Date: 2026-07-16
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None

# module -> (action, [role names]) — permisos NUEVOS de esta fase. `absence_requests:create`
# va a todos los roles internos vinculados a un Recurso (no a `Encargado`, contacto externo).
NEW_PERMISSIONS = {
    ("absence_requests", "create"): ["Admin", "Coordinador", "QM", "Resolutor", "RRHH"],
    ("absence_requests", "view_all"): ["RRHH"],
    ("absence_requests", "decide_hr"): ["RRHH"],
    ("holidays", "manage"): ["Admin", "RRHH"],
}


def upgrade() -> None:
    bind = op.get_bind()

    rrhh_id = uuid.uuid4()
    bind.execute(
        sa.text("INSERT INTO roles (id, name, description) VALUES (:id, :name, :description)"),
        {"id": str(rrhh_id), "name": "RRHH",
         "description": "Recursos Humanos: aprueba/rechaza solicitudes de ausencia del equipo"},
    )

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
        "(SELECT id FROM permissions WHERE module = 'absence_requests') "
        "OR permission_id IN (SELECT id FROM permissions WHERE module = 'holidays')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE module IN ('absence_requests', 'holidays')"))
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE role_id IN (SELECT id FROM roles WHERE name = 'RRHH')"
    ))
    bind.execute(sa.text("DELETE FROM roles WHERE name = 'RRHH'"))
