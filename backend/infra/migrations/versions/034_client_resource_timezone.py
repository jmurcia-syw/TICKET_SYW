"""clients.timezone/country + resources.timezone (Fase 5 SDD V3, spec 020)

Revision ID: 034
Revises: 033
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("timezone", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("country", sa.Text(), nullable=True))
    op.add_column("resources", sa.Column("timezone", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("resources", "timezone")
    op.drop_column("clients", "country")
    op.drop_column("clients", "timezone")
