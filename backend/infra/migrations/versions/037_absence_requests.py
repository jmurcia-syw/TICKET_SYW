"""absence_requests + absence_request_attachments (Fase 5 SDD V3, spec 020, data-model.md)

Revision ID: 037
Revises: 036
Create Date: 2026-07-16

`overall_status` no se persiste — se deriva en `backend/domain/services/absence_service.py`
(research.md Decisión 4) a partir de `manager_status`/`hr_status`.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "absence_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("absence_type_id", UUID(as_uuid=True), sa.ForeignKey("catalog_absence_types.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("manager_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("manager_decided_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("manager_decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("hr_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("hr_decided_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("hr_decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_check_constraint(
        "ck_absence_requests_manager_status", "absence_requests",
        "manager_status IN ('pending','approved','rejected')")
    op.create_check_constraint(
        "ck_absence_requests_hr_status", "absence_requests",
        "hr_status IN ('pending','approved','rejected')")
    op.create_check_constraint(
        "ck_absence_requests_date_order", "absence_requests", "end_date >= start_date")

    op.create_table(
        "absence_request_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("absence_request_id", UUID(as_uuid=True), sa.ForeignKey("absence_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("absence_request_attachments")
    op.drop_constraint("ck_absence_requests_date_order", "absence_requests", type_="check")
    op.drop_constraint("ck_absence_requests_hr_status", "absence_requests", type_="check")
    op.drop_constraint("ck_absence_requests_manager_status", "absence_requests", type_="check")
    op.drop_table("absence_requests")
