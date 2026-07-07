"""add reset_token + reset_token_expires_at to users (self-service password recovery)

Revision ID: 014
Revises: 013
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reset_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("reset_token_expires_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_reset_token", "users", ["reset_token"])


def downgrade() -> None:
    op.drop_constraint("uq_users_reset_token", "users", type_="unique")
    op.drop_column("users", "reset_token_expires_at")
    op.drop_column("users", "reset_token")
