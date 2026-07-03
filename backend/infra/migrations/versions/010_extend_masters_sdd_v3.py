"""extend masters per SDD V3: client billing + systems, project financials, resource extended profile + compensation, compensation permissions

Revision ID: 010
Revises: 009
Create Date: 2026-07-02
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

COMPENSATION_MODULE = "compensation"
COMPENSATION_ACTIONS = ["view", "edit"]


def upgrade() -> None:
    bind = op.get_bind()

    # ── clients: facturacion anual (FR-028) ────────────────────────────
    op.add_column("clients", sa.Column("annual_billing_usd", sa.Numeric(14, 2), nullable=True))

    # ── client_systems: portafolio de software del cliente (FR-029) ────
    op.create_table(
        "client_systems",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("system_type", sa.Text(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_client_systems_client_id", "client_systems", ["client_id"])

    # ── projects: overview + financieros + componentes (FR-030) ────────
    op.add_column("projects", sa.Column("overview", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("sale_services_usd", sa.Numeric(14, 2), nullable=True))
    op.add_column("projects", sa.Column("sale_licenses_usd", sa.Numeric(14, 2), nullable=True))
    op.add_column("projects", sa.Column("sale_subscriptions_usd", sa.Numeric(14, 2), nullable=True))
    op.add_column("projects", sa.Column("components_sold", sa.Text(), nullable=True))

    # ── resources: perfil extendido (FR-031) ───────────────────────────
    op.add_column("resources", sa.Column("identification", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("nationality", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("resources", sa.Column("marital_status", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("contract_type", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("calendar_country", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("education_level", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("specialty", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("seniority", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("certifications", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("team", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("manager_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=True))
    op.create_check_constraint("ck_resources_manager_not_self", "resources", "manager_id IS NULL OR manager_id <> id")

    # ── resource_compensation: area protegida cifrada (FR-032) ─────────
    op.create_table(
        "resource_compensation",
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), primary_key=True),
        sa.Column("base_salary", sa.LargeBinary(), nullable=True),
        sa.Column("total_salary", sa.LargeBinary(), nullable=True),
        sa.Column("overhead", sa.LargeBinary(), nullable=True),
        sa.Column("hourly_cost", sa.LargeBinary(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── seed permisos compensation:view/edit solo para el rol Admin (FR-033) ──
    admin_role = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'Admin'")).fetchone()
    if admin_role is None:
        raise RuntimeError("No existe el rol 'Admin'; ejecutar migracion 009 primero")
    for action in COMPENSATION_ACTIONS:
        perm_id = uuid.uuid4()
        bind.execute(
            sa.text("INSERT INTO permissions (id, module, action) VALUES (:id, :module, :action)"),
            {"id": str(perm_id), "module": COMPENSATION_MODULE, "action": action},
        )
        bind.execute(
            sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
            {"role_id": str(admin_role.id), "permission_id": str(perm_id)},
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE module = :module)"
    ), {"module": COMPENSATION_MODULE})
    bind.execute(sa.text("DELETE FROM permissions WHERE module = :module"), {"module": COMPENSATION_MODULE})
    op.drop_table("resource_compensation")
    op.drop_constraint("ck_resources_manager_not_self", "resources", type_="check")
    for col in ("manager_id", "team", "certifications", "seniority", "specialty", "education_level",
                "calendar_country", "contract_type", "marital_status", "birth_date", "nationality",
                "identification"):
        op.drop_column("resources", col)
    for col in ("components_sold", "sale_subscriptions_usd", "sale_licenses_usd", "sale_services_usd", "overview"):
        op.drop_column("projects", col)
    op.drop_index("ix_client_systems_client_id", table_name="client_systems")
    op.drop_table("client_systems")
    op.drop_column("clients", "annual_billing_usd")
