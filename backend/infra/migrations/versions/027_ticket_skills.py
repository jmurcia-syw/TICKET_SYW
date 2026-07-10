"""skills requeridas del ticket (opcional)

Revision ID: 027
Revises: 026
Create Date: 2026-07-10

Spec 011 — tabla puente `ticket_skills` (N:M), mismo patrón que `resource_skills` (migración
004): asocia opcionalmente Skills del catálogo existente (spec 010) a un Ticket/Tarea/Subtarea
(misma tabla `tickets`, spec 008). Sin backfill: todos los tickets existentes quedan con cero
Skills requeridas por defecto (SC-002). No modifica ninguna tabla existente.

`skill_id` NO tiene `ON DELETE CASCADE` (a diferencia de `ticket_id`) — a propósito, mismo
criterio que `resource_skills.skill_id`: un Skill referenciado por algún ticket no debe poder
borrarse en silencio (ver el chequeo `skill_in_use` agregado a `DELETE /api/skills/{id}` en
`backend/api/routes/resources.py`, que ahora también considera tickets, no solo recursos).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_skills",
        sa.Column("ticket_id", UUID(as_uuid=True),
                  sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, primary_key=True),
        sa.Column("skill_id", UUID(as_uuid=True),
                  sa.ForeignKey("skills.id"), nullable=False, primary_key=True),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("ticket_skills")
