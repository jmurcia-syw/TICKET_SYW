"""Permiso tickets:view_assigned para Resolutor (spec 038, US1)

Revision ID: 052
Revises: 051
Create Date: 2026-08-05

El rol Resolutor tenía `tickets:view` (acceso global al listado de Tickets/Tareas), lo que le
permitía ver el listado completo del sistema por defecto. La spec 038 (FR-003/FR-004) restringe
la vista global de "Tickets" a Coordinador/Admin: se agrega un permiso nuevo y explícito
`tickets:view_assigned` (Resolutor) — con solo este permiso, el listado se fuerza server-side a
`assignee_id = <resource_id del actor>` (ver `backend/api/routes/tickets.py`) — y se retira el
vínculo `Resolutor` -> `tickets:view` si existía. No se toca `tickets:view_own` (Usuario/cliente,
migración 021, scoping por `client_contact_id`) ni la política RLS de `tickets` (migración 012,
deliberadamente permisiva — ver research.md Decisión 1 de la spec 038).
"""
from alembic import op
import sqlalchemy as sa

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None

NEW_PERMISSION = ("tickets", "view_assigned")
NEW_PERMISSION_ROLES = ["Resolutor"]
REMOVED_ROLE = "Resolutor"
REMOVED_PERMISSION = ("tickets", "view")


def upgrade() -> None:
    bind = op.get_bind()
    roles = {r.name: r.id for r in bind.execute(sa.text("SELECT id, name FROM roles")).fetchall()}

    permission_id = bind.execute(sa.text(
        "SELECT id FROM permissions WHERE module = :m AND action = :a"
    ), {"m": NEW_PERMISSION[0], "a": NEW_PERMISSION[1]}).scalar()
    if not permission_id:
        permission_id = bind.execute(sa.text(
            "INSERT INTO permissions (id, module, action) VALUES (gen_random_uuid(), :m, :a) "
            "RETURNING id"
        ), {"m": NEW_PERMISSION[0], "a": NEW_PERMISSION[1]}).scalar()

    for role_name in NEW_PERMISSION_ROLES:
        role_id = roles.get(role_name)
        if not role_id:
            continue
        exists = bind.execute(sa.text(
            "SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"
        ), {"r": str(role_id), "p": str(permission_id)}).first()
        if not exists:
            bind.execute(
                sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                {"r": str(role_id), "p": str(permission_id)},
            )

    removed_role_id = roles.get(REMOVED_ROLE)
    if removed_role_id:
        bind.execute(sa.text(
            "DELETE FROM role_permissions WHERE role_id = :r AND permission_id IN "
            "(SELECT id FROM permissions WHERE module = :m AND action = :a)"
        ), {"r": str(removed_role_id), "m": REMOVED_PERMISSION[0], "a": REMOVED_PERMISSION[1]})


def downgrade() -> None:
    bind = op.get_bind()
    roles = {r.name: r.id for r in bind.execute(sa.text("SELECT id, name FROM roles")).fetchall()}

    view_permission_id = bind.execute(sa.text(
        "SELECT id FROM permissions WHERE module = :m AND action = :a"
    ), {"m": REMOVED_PERMISSION[0], "a": REMOVED_PERMISSION[1]}).scalar()
    removed_role_id = roles.get(REMOVED_ROLE)
    if view_permission_id and removed_role_id:
        exists = bind.execute(sa.text(
            "SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"
        ), {"r": str(removed_role_id), "p": str(view_permission_id)}).first()
        if not exists:
            bind.execute(
                sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                {"r": str(removed_role_id), "p": str(view_permission_id)},
            )

    view_assigned_permission_id = bind.execute(sa.text(
        "SELECT id FROM permissions WHERE module = :m AND action = :a"
    ), {"m": NEW_PERMISSION[0], "a": NEW_PERMISSION[1]}).scalar()
    if view_assigned_permission_id:
        bind.execute(sa.text(
            "DELETE FROM role_permissions WHERE permission_id = :p"
        ), {"p": str(view_assigned_permission_id)})
        bind.execute(sa.text(
            "DELETE FROM permissions WHERE id = :p"
        ), {"p": str(view_assigned_permission_id)})
