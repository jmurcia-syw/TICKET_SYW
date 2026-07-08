"""add client_contact_id to tickets (Fase 2.2 — Encargado solicitante asignable manualmente)

Revision ID: 022
Revises: 021
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("client_contact_id", UUID(as_uuid=True),
                  sa.ForeignKey("client_contacts.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tickets", "client_contact_id")
