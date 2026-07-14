"""SLAs por Proyecto y Prioridad (Fase 4 — spec 014)

Revision ID: 028
Revises: 027
Create Date: 2026-07-14

Crea la tabla `sla_rules` (regla de tiempos límite por Proyecto+Prioridad, data-model.md) y agrega
las columnas `sla_*` a `tickets` para el snapshot incremental de consumo de la fase de SLA vigente
(research.md Decisión 1, revisada 2026-07-14: modelo de 2 fases). Sin backfill: los tickets
existentes quedan con `sla_status='sin_sla'` por defecto (no hay reglas creadas todavía).

También siembra el permiso `sla_rules:manage` para Admin/Coordinador (FR-013), mismo patrón que
017_work_sessions_permissions.py.
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None

PERMISSION_MATRIX = {
    ("sla_rules", "manage"): ["Admin", "Coordinador"],
}


def upgrade() -> None:
    op.create_table(
        "sla_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("contact_minutes", sa.Integer(), nullable=False),
        sa.Column("execution_minutes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "priority", name="uq_sla_rules_project_priority"),
    )
    op.create_check_constraint(
        "ck_sla_rules_priority", "sla_rules",
        "priority IN ('critical','high','medium','low')")
    op.create_check_constraint(
        "ck_sla_rules_positive_minutes", "sla_rules",
        "contact_minutes > 0 AND execution_minutes > 0")

    op.add_column("tickets", sa.Column("sla_rule_id", UUID(as_uuid=True),
                                        sa.ForeignKey("sla_rules.id"), nullable=True))
    op.add_column("tickets", sa.Column("sla_phase", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("sla_phase_limit_minutes", sa.Integer(), nullable=True))
    op.add_column("tickets", sa.Column("sla_consumed_seconds", sa.Integer(),
                                        nullable=False, server_default="0"))
    op.add_column("tickets", sa.Column("sla_last_resume_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("sla_status", sa.Text(),
                                        nullable=False, server_default="sin_sla"))
    op.add_column("tickets", sa.Column("sla_contact_result", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("sla_contact_consumed_seconds", sa.Integer(), nullable=True))

    op.create_check_constraint(
        "ck_tickets_sla_phase", "tickets",
        "sla_phase IS NULL OR sla_phase IN ('contacto','ejecucion','cerrado')")
    op.create_check_constraint(
        "ck_tickets_sla_status", "tickets",
        "sla_status IN ('sin_sla','corriendo','pausado','vencido','detenido')")
    op.create_check_constraint(
        "ck_tickets_sla_contact_result", "tickets",
        "sla_contact_result IS NULL OR sla_contact_result IN ('pendiente','cumplido','vencido')")

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
        "(SELECT id FROM permissions WHERE module = 'sla_rules')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'sla_rules'"))

    op.drop_constraint("ck_tickets_sla_contact_result", "tickets", type_="check")
    op.drop_constraint("ck_tickets_sla_status", "tickets", type_="check")
    op.drop_constraint("ck_tickets_sla_phase", "tickets", type_="check")
    op.drop_column("tickets", "sla_contact_consumed_seconds")
    op.drop_column("tickets", "sla_contact_result")
    op.drop_column("tickets", "sla_status")
    op.drop_column("tickets", "sla_last_resume_at")
    op.drop_column("tickets", "sla_consumed_seconds")
    op.drop_column("tickets", "sla_phase_limit_minutes")
    op.drop_column("tickets", "sla_phase")
    op.drop_column("tickets", "sla_rule_id")

    op.drop_table("sla_rules")
