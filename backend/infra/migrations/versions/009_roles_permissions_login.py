"""create roles, permissions, role_permissions; migrate users off fixed role enum; add username/password_hash; seed data

Revision ID: 009
Revises: 008
Create Date: 2026-07-01
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

# Contraseña fija para los 4 usuarios semilla en Dev/Test/Prod Docker Compose locales — ver
# docs/credenciales_dev.txt. DEBE rotarse manualmente (endpoint reset-password) antes de operar
# la Producción real en el servidor Ubuntu con datos de clientes reales (TODO(HOSTING)).
SEED_PASSWORD_DEV = "SyWork_Dev2026!"

MODULES = ["clients", "projects", "resources", "skills", "users", "roles"]
ACTIONS = ["view", "create", "edit", "deactivate"]

ROLE_PROFILES = {
    "Admin": {m: list(ACTIONS) for m in MODULES},
    "Coordinador": {
        "clients": list(ACTIONS), "projects": list(ACTIONS), "resources": list(ACTIONS),
        "skills": list(ACTIONS), "users": ["view"], "roles": [],
    },
    "QM": {
        "clients": list(ACTIONS), "projects": ["view"], "resources": list(ACTIONS),
        "skills": list(ACTIONS), "users": ["view"], "roles": [],
    },
    "Resolutor": {
        "clients": ["view"], "projects": ["view"], "resources": ["view"],
        "skills": ["view"], "users": ["view"], "roles": [],
    },
}

SEED_USERS = [
    ("admin@sywork.net", "admin", "Admin"),
    ("coordinador@sywork.net", "coordinador", "Coordinador"),
    ("qm@sywork.net", "qm", "QM"),
    ("resolutor@sywork.net", "resolutor", "Resolutor"),
]

OLD_ROLE_TO_NEW_NAME = {
    "admin": "Admin", "coordinator": "Coordinador", "qm": "QM", "resolver": "Resolutor",
}


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("module", "action", name="uq_permissions_module_action"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False, primary_key=True),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("permissions.id"), nullable=False, primary_key=True),
    )

    op.add_column("users", sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=True))
    op.add_column("users", sa.Column("username", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))

    # ── seed roles ──────────────────────────────────────────────────────
    role_ids = {}
    for name in ROLE_PROFILES:
        role_id = uuid.uuid4()
        role_ids[name] = role_id
        bind.execute(
            sa.text("INSERT INTO roles (id, name, description) VALUES (:id, :name, :description)"),
            {"id": str(role_id), "name": name, "description": f"Rol {name}"},
        )

    # ── seed permissions (6 modules x 4 actions = 24) ──────────────────
    permission_ids = {}
    for module in MODULES:
        for action in ACTIONS:
            perm_id = uuid.uuid4()
            permission_ids[(module, action)] = perm_id
            bind.execute(
                sa.text("INSERT INTO permissions (id, module, action) VALUES (:id, :module, :action)"),
                {"id": str(perm_id), "module": module, "action": action},
            )

    # ── seed role_permissions matrix ───────────────────────────────────
    for role_name, module_actions in ROLE_PROFILES.items():
        for module, actions in module_actions.items():
            for action in actions:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"
                    ),
                    {"role_id": str(role_ids[role_name]), "permission_id": str(permission_ids[(module, action)])},
                )

    # ── backfill existing users onto the new role_id/username columns ──
    existing_users = bind.execute(sa.text("SELECT id, email, role FROM users")).fetchall()
    for row in existing_users:
        new_role_name = OLD_ROLE_TO_NEW_NAME.get(row.role)
        if new_role_name is None:
            raise RuntimeError(f"Usuario {row.email} tiene un role desconocido: {row.role!r}")
        username = row.email.split("@")[0]
        bind.execute(
            sa.text("UPDATE users SET role_id = :role_id, username = :username WHERE id = :id"),
            {"role_id": str(role_ids[new_role_name]), "username": username, "id": str(row.id)},
        )

    # ── seed the 4 login users (una sola contraseña fija, ver SEED_PASSWORD_DEV arriba) ──
    password_hash = generate_password_hash(SEED_PASSWORD_DEV)
    for email, username, role_name in SEED_USERS:
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, username, role_id, password_hash, active) "
                "VALUES (:id, :email, :username, :role_id, :password_hash, true) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()), "email": email, "username": username,
                "role_id": str(role_ids[role_name]), "password_hash": password_hash,
            },
        )

    print("=" * 70)
    print("Usuarios semilla creados (admin/coordinador/qm/resolutor).")
    print("Contraseña fija documentada en docs/credenciales_dev.txt — rotarla antes de")
    print("operar la Producción real con datos de clientes reales.")
    print("=" * 70)

    # ── finalize users schema ──────────────────────────────────────────
    op.alter_column("users", "role_id", nullable=False)
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column("users", sa.Column("role", sa.Text(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE users u SET role = CASE r.name
            WHEN 'Admin' THEN 'admin'
            WHEN 'Coordinador' THEN 'coordinator'
            WHEN 'QM' THEN 'qm'
            WHEN 'Resolutor' THEN 'resolver'
        END
        FROM roles r WHERE u.role_id = r.id
    """))
    op.alter_column("users", "role", nullable=False, server_default="resolver")
    op.create_check_constraint("ck_users_role", "users", "role IN ('admin','coordinator','qm','resolver')")
    seed_emails = ",".join(f"'{email}'" for email, _, _ in SEED_USERS)
    op.execute(f"DELETE FROM users WHERE email IN ({seed_emails})")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
    op.drop_column("users", "role_id")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
