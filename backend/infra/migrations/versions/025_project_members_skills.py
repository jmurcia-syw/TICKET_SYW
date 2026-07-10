"""renombre rol Encargado→Usuario/cliente + personal del proyecto (members/teams) +
estructura de skills (tipo/herramienta/proceso) con backfill y semillas

Revision ID: 025
Revises: 024
Create Date: 2026-07-09

Spec 010 — orden de operaciones según data-model.md:
1. UPDATE roles (renombre in-place, mismo UUID: role_permissions y users.role_id intactos).
2-4. project_members / project_teams / project_team_members (cascades) + RLS.
5. Backfill de membresías desde tickets con solicitante y proyecto (FR-006).
6-7. skills += skill_type (backfill + NOT NULL + CHECK), tool_id, process_id.
8. catalog_processes += Compras, Mantenimiento (si no existen).
9. Upsert de 10 skills semilla por code (research.md Decisión 5).
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None

# code: (label, tool_name | None, process_name | None, skill_type)
SEED_SKILLS = {
    "JDE_GL": ("JDE General Ledger", "JDE", "Finanzas", "funcional"),
    "JDE_AP": ("JDE Accounts Payable", "JDE", "Compras", "funcional"),
    "JDE_MTC": ("JDE Maintenance Mgmt", "JDE", "Mantenimiento", "funcional"),
    "BSFN": ("JDE Business Functions (dev)", "JDE", None, "tecnico"),
    "SQL_JDE": ("SQL sobre JDE", "JDE", None, "tecnico"),
    "OIC": ("Oracle Integration Cloud", "Oracle Fusion", "Integraciones", "tecnico"),
    "APEX": ("Oracle APEX (genérico)", None, None, "tecnico"),
    "BI": ("Business Intelligence (genérico)", None, None, "tecnico"),
    "JAVA_PYTHON_REACT": ("Java / Python / React (genérico)", None, None, "tecnico"),
    "DBA": ("Admin. BD (genérico)", None, None, "tecnico"),
}

# Backfill de tipo para skills preexistentes no cubiertas por las semillas (spec Assumption)
FUNCTIONAL_BACKFILL = ("JDE_AR", "ORACLE_CRM")

NEW_PROCESSES = ("Compras", "Mantenimiento")

RLS_TABLES = ("project_members", "project_teams", "project_team_members")


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Renombre del rol (mismo UUID — FR-002) ───────────────────────────
    bind.execute(sa.text(
        "UPDATE roles SET name = 'Usuario/cliente', "
        "description = 'Usuario externo de un Cliente: solo crea y ve sus propios tickets' "
        "WHERE name = 'Encargado'"
    ))

    # ── 2. project_members ──────────────────────────────────────────────────
    op.create_table(
        "project_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])

    # ── 3. project_teams ────────────────────────────────────────────────────
    op.create_table(
        "project_teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "name", name="uq_project_teams_project_name"),
    )
    op.create_index("ix_project_teams_project_id", "project_teams", ["project_id"])

    # ── 4. project_team_members (cascades: ver data-model.md invariantes) ───
    op.create_table(
        "project_team_members",
        sa.Column("team_id", UUID(as_uuid=True),
                  sa.ForeignKey("project_teams.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", UUID(as_uuid=True),
                  sa.ForeignKey("project_members.id", ondelete="CASCADE"), primary_key=True),
    )

    # RLS app-level, mismo patron que 020_client_contacts_rls.py
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_app_access ON {table} "
            f"USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' "
            f"OR current_user = 'sywork_user')"
        )

    # ── 5. Backfill: cada Usuario/cliente queda vinculado a los proyectos donde
    #      ya figura como solicitante de tickets (FR-006 / SC-003) ───────────
    op.execute("""
        INSERT INTO project_members (project_id, user_id)
        SELECT DISTINCT t.project_id, cc.user_id
        FROM tickets t
        JOIN client_contacts cc ON cc.id = t.client_contact_id
        WHERE t.project_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_project_members_project_user DO NOTHING
    """)

    # ── 6. skills: columnas nuevas (nullable primero para poder backfillear) ─
    op.add_column("skills", sa.Column("skill_type", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("tool_id", UUID(as_uuid=True),
                                      sa.ForeignKey("catalog_tools.id"), nullable=True))
    op.add_column("skills", sa.Column("process_id", UUID(as_uuid=True),
                                      sa.ForeignKey("catalog_processes.id"), nullable=True))

    # ── 7. Backfill de tipo (FR-017) + NOT NULL + CHECK ─────────────────────
    functional = ", ".join(f"'{c}'" for c in FUNCTIONAL_BACKFILL)
    op.execute(f"UPDATE skills SET skill_type = 'funcional' WHERE code IN ({functional})")
    op.execute("UPDATE skills SET skill_type = 'tecnico' WHERE skill_type IS NULL")
    op.alter_column("skills", "skill_type", nullable=False)
    op.create_check_constraint("ck_skills_type", "skills", "skill_type IN ('funcional','tecnico')")

    # ── 8. Procesos requeridos por las semillas (FR-016) ────────────────────
    for process in NEW_PROCESSES:
        bind.execute(
            sa.text("INSERT INTO catalog_processes (id, name) "
                    "SELECT :id, :name WHERE NOT EXISTS "
                    "(SELECT 1 FROM catalog_processes WHERE name = :name)"),
            {"id": str(uuid.uuid4()), "name": process},
        )

    # ── 9. Semillas de skills: upsert por code (FR-015 — JDE_GL/JDE_AP se
    #      actualizan, no se duplican) ───────────────────────────────────────
    for code, (label, tool_name, process_name, skill_type) in SEED_SKILLS.items():
        bind.execute(
            sa.text("""
                INSERT INTO skills (id, code, label, active, skill_type, tool_id, process_id)
                VALUES (
                    :id, :code, :label, true, :skill_type,
                    (SELECT id FROM catalog_tools WHERE name = :tool_name),
                    (SELECT id FROM catalog_processes WHERE name = :process_name)
                )
                ON CONFLICT ON CONSTRAINT uq_skills_code DO UPDATE SET
                    label = EXCLUDED.label,
                    skill_type = EXCLUDED.skill_type,
                    tool_id = EXCLUDED.tool_id,
                    process_id = EXCLUDED.process_id,
                    active = true
            """),
            {"id": str(uuid.uuid4()), "code": code, "label": label, "skill_type": skill_type,
             "tool_name": tool_name, "process_name": process_name},
        )


def downgrade() -> None:
    # Las semillas de skills y los procesos nuevos quedan (datos de catálogo, mismo
    # criterio que migraciones previas); se revierte esquema y renombre.
    op.drop_constraint("ck_skills_type", "skills", type_="check")
    op.drop_column("skills", "process_id")
    op.drop_column("skills", "tool_id")
    op.drop_column("skills", "skill_type")

    for table in reversed(RLS_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_app_access ON {table}")

    op.drop_table("project_team_members")
    op.drop_index("ix_project_teams_project_id", table_name="project_teams")
    op.drop_table("project_teams")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_table("project_members")

    op.get_bind().execute(sa.text(
        "UPDATE roles SET name = 'Encargado', "
        "description = 'Contacto externo de un Cliente: solo crea y ve sus propios tickets' "
        "WHERE name = 'Usuario/cliente'"
    ))
