"""seed rol Encargado, permisos tickets:view_own/client_contacts:manage, extender
tickets:create; relajar el dominio de email fijo (Encargado usa su email real externo)

Revision ID: 021
Revises: 020
Create Date: 2026-07-08
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None

# module -> (action, [role names]) — permisos NUEVOS de esta fase
NEW_PERMISSIONS = {
    ("tickets", "view_own"): ["Encargado"],
    ("client_contacts", "manage"): ["Admin", "Coordinador"],
}


def upgrade() -> None:
    bind = op.get_bind()

    # ── rol Encargado ───────────────────────────────────────────────────
    encargado_id = uuid.uuid4()
    bind.execute(
        sa.text("INSERT INTO roles (id, name, description) VALUES (:id, :name, :description)"),
        {"id": str(encargado_id), "name": "Encargado",
         "description": "Contacto externo de un Cliente: solo crea y ve sus propios tickets"},
    )

    roles = {r.name: r.id for r in bind.execute(sa.text("SELECT id, name FROM roles")).fetchall()}

    # ── permisos nuevos ─────────────────────────────────────────────────
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

    # ── extender tickets:create (ya existente) al rol Encargado ────────
    tickets_create = bind.execute(
        sa.text("SELECT id FROM permissions WHERE module = 'tickets' AND action = 'create'")
    ).fetchone()
    if tickets_create:
        bind.execute(
            sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
            {"r": str(encargado_id), "p": str(tickets_create.id)},
        )

    # ── el Encargado usa su email real externo, no @sywork.net ─────────
    # (la restriccion de dominio para el resto de roles internos se mantiene a nivel de
    # aplicacion en backend/api/routes/users.py — ALLOWED_EMAIL_DOMAIN — sin cambios)
    op.drop_constraint("ck_users_email_domain", "users", type_="check")


def downgrade() -> None:
    op.create_check_constraint("ck_users_email_domain", "users", "email LIKE '%@sywork.net'")

    bind = op.get_bind()
    encargado = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'Encargado'")).fetchone()
    if encargado:
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE role_id = :r"), {"r": str(encargado.id)}
        )
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE module = 'client_contacts') "
        "OR permission_id IN (SELECT id FROM permissions WHERE module = 'tickets' AND action = 'view_own')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'client_contacts'"))
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'tickets' AND action = 'view_own'"))
    if encargado:
        bind.execute(sa.text("DELETE FROM roles WHERE id = :r"), {"r": str(encargado.id)})
