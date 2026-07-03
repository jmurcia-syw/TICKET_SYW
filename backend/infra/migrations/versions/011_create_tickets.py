"""create tickets core: tickets, comments, attachments, transitions, assignments, notifications, catalogs + permission seed

Revision ID: 011
Revises: 010
Create Date: 2026-07-02
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

STATUSES = (
    "nuevo", "pre_analisis", "contacto", "en_analisis", "en_ejecucion",
    "en_pruebas", "pendiente_usuario", "resuelto", "cerrado", "cancelado",
)
COMMENT_TYPES = (
    "asignado", "pre_analisis", "confirmacion_atencion", "solicitud_informacion",
    "termina_analisis", "solicitud_cierre", "respuesta_usuario",
    "descripcion_solucion", "comentario_interno", "cancelacion",
)

CATALOG_SEEDS = {
    "catalog_tools": ["JDE", "Oracle Fusion", "OTM", "Otro"],
    "catalog_processes": ["Finanzas", "Logística", "Manufactura", "Integraciones", "Otro"],
    "catalog_resolution_types": [
        "Solución definitiva", "Workaround", "Configuración", "Datos",
        "No es incidente", "Sin respuesta de usuario",
    ],
}

# módulo -> (acciones, roles por acción)
TICKET_ACTIONS = ["view", "create", "edit", "assign", "transition", "cancel"]
PERMISSION_MATRIX = {
    # (module, action): [role names]
    **{("tickets", a): ["Admin", "Coordinador"] for a in TICKET_ACTIONS},
    ("assignment_panel", "view"): ["Admin", "Coordinador", "QM"],
    ("catalogs", "view"): ["Admin", "Coordinador", "QM", "Resolutor"],
    ("catalogs", "create"): ["Admin", "Coordinador"],
    ("catalogs", "deactivate"): ["Admin", "Coordinador"],
}
# QM: todo tickets menos cancel
for a in TICKET_ACTIONS:
    if a != "cancel":
        PERMISSION_MATRIX[("tickets", a)] = PERMISSION_MATRIX[("tickets", a)] + ["QM"]
# Resolutor: view, create, transition (regla "solo asignados" vive en dominio)
for a in ("view", "create", "transition"):
    PERMISSION_MATRIX[("tickets", a)] = PERMISSION_MATRIX[("tickets", a)] + ["Resolutor"]


def _catalog_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def upgrade() -> None:
    bind = op.get_bind()

    for table in CATALOG_SEEDS:
        _catalog_table(table)
        for value in CATALOG_SEEDS[table]:
            bind.execute(
                sa.text(f"INSERT INTO {table} (id, name) VALUES (:id, :name)"),
                {"id": str(uuid.uuid4()), "name": value},
            )

    op.execute("CREATE SEQUENCE ticket_number_seq START 1")

    status_check = ", ".join(f"'{s}'" for s in STATUSES)
    op.create_table(
        "tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_number", sa.BigInteger(), nullable=False, unique=True,
                  server_default=sa.text("nextval('ticket_number_seq')")),
        sa.Column("record_type", sa.Text(), nullable=False, server_default="ticket"),
        sa.Column("ticket_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="nuevo"),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("escalation_level", sa.Text(), nullable=False, server_default="n2"),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("tool_id", UUID(as_uuid=True), sa.ForeignKey("catalog_tools.id"), nullable=True),
        sa.Column("process_id", UUID(as_uuid=True), sa.ForeignKey("catalog_processes.id"), nullable=True),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=True),
        sa.Column("estimated_resolution_minutes", sa.Integer(), nullable=True),
        sa.Column("resolution_type_id", UUID(as_uuid=True), sa.ForeignKey("catalog_resolution_types.id"), nullable=True),
        sa.Column("related_ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolution_accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(f"status IN ({status_check})", name="ck_tickets_status"),
        sa.CheckConstraint("record_type IN ('ticket','task')", name="ck_tickets_record_type"),
        sa.CheckConstraint("ticket_type IN ('incident','evolutive','preventive')", name="ck_tickets_type"),
        sa.CheckConstraint("priority IN ('critical','high','medium','low')", name="ck_tickets_priority"),
        sa.CheckConstraint("severity IN ('s1','s2','s3','s4')", name="ck_tickets_severity"),
        sa.CheckConstraint("escalation_level IN ('n1','n2','n3','n4')", name="ck_tickets_level"),
        sa.CheckConstraint("estimated_resolution_minutes IS NULL OR estimated_resolution_minutes >= 0",
                           name="ck_tickets_estimate"),
        sa.CheckConstraint("related_ticket_id IS NULL OR related_ticket_id <> id", name="ck_tickets_related_not_self"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_client_id", "tickets", ["client_id"])
    op.create_index("ix_tickets_assignee_id", "tickets", ["assignee_id"])
    op.create_index("ix_tickets_assignee_status", "tickets", ["assignee_id", "status"])

    comment_check = ", ".join(f"'{c}'" for c in COMMENT_TYPES)
    op.create_table(
        "ticket_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("comment_type", sa.Text(), nullable=False),
        sa.Column("visibility", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_automatic", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(f"comment_type IN ({comment_check})", name="ck_comments_type"),
        sa.CheckConstraint("visibility IN ('internal','external')", name="ck_comments_visibility"),
    )
    op.create_index("ix_ticket_comments_ticket_id", "ticket_comments", ["ticket_id"])

    op.create_table(
        "comment_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comment_id", UUID(as_uuid=True), sa.ForeignKey("ticket_comments.id"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "ticket_status_transitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comment_id", UUID(as_uuid=True), sa.ForeignKey("ticket_comments.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_transitions_ticket_id", "ticket_status_transitions", ["ticket_id"])

    op.create_table(
        "ticket_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("assigner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("resulting_status", sa.Text(), nullable=False),
        sa.Column("context", JSONB(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_assignments_ticket_id", "ticket_assignments", ["ticket_id"])

    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read"])

    # ── seed de permisos ────────────────────────────────────────────────
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
        "(SELECT id FROM permissions WHERE module IN ('tickets','assignment_panel','catalogs'))"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE module IN ('tickets','assignment_panel','catalogs')"))
    for table in ("notifications", "ticket_assignments", "ticket_status_transitions",
                  "comment_attachments", "ticket_comments", "tickets"):
        op.drop_table(table)
    op.execute("DROP SEQUENCE ticket_number_seq")
    for table in ("catalog_resolution_types", "catalog_processes", "catalog_tools"):
        op.drop_table(table)
