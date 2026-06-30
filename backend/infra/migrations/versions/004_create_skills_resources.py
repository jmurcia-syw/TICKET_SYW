"""create skills, resources, resource_skills tables

Revision ID: 004
Revises: 003
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_skills_code"),
    )

    op.create_table(
        "resources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, unique=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_resources_email"),
        sa.CheckConstraint("email LIKE '%@sywork.net'", name="ck_resources_email_domain"),
    )
    op.execute("ALTER TABLE resources ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "resource_skills",
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=False, primary_key=True),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id"), nullable=False, primary_key=True),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Seed initial skills
    op.execute("""
        INSERT INTO skills (code, label) VALUES
        ('JDE_GL', 'JDE General Ledger'),
        ('JDE_AP', 'JDE Accounts Payable'),
        ('JDE_AR', 'JDE Accounts Receivable'),
        ('ORACLE_FUSION', 'Oracle Fusion'),
        ('ORACLE_CRM', 'Oracle CRM'),
        ('API_REST', 'API REST Integration'),
        ('SQL_ORACLE', 'SQL / Oracle DB'),
        ('ORCHESTRATOR', 'Orchestrator / RPA')
    """)


def downgrade() -> None:
    op.drop_table("resource_skills")
    op.drop_table("resources")
    op.drop_table("skills")
