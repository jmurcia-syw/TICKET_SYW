"""add started_at/ended_at to work_sessions (Fase 2.1 — registro estilo Teamwork)

Revision ID: 018
Revises: 017
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("work_sessions", sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("work_sessions", sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("work_sessions", "ended_at")
    op.drop_column("work_sessions", "started_at")
