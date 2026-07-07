"""dynamic record type catalog: catalog_record_types + tickets.record_type_id (FR-029/FR-030)

Revision ID: 013
Revises: 012
Create Date: 2026-07-06
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

RECORD_TYPE_SEEDS = ["Ticket", "Tarea"]  # Tarea reservado para Fase 3 (FR-030)


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "catalog_record_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    seed_ids: dict[str, str] = {}
    for name in RECORD_TYPE_SEEDS:
        new_id = str(uuid.uuid4())
        seed_ids[name] = new_id
        bind.execute(
            sa.text("INSERT INTO catalog_record_types (id, name) VALUES (:id, :name)"),
            {"id": new_id, "name": name},
        )

    op.add_column("tickets", sa.Column("record_type_id", UUID(as_uuid=True), nullable=True))
    bind.execute(
        sa.text("UPDATE tickets SET record_type_id = :ticket_id WHERE record_type = 'ticket'"),
        {"ticket_id": seed_ids["Ticket"]},
    )
    bind.execute(
        sa.text("UPDATE tickets SET record_type_id = :task_id WHERE record_type = 'task'"),
        {"task_id": seed_ids["Tarea"]},
    )
    op.alter_column("tickets", "record_type_id", nullable=False)
    op.create_foreign_key(
        "fk_tickets_record_type_id", "tickets", "catalog_record_types", ["record_type_id"], ["id"])

    op.drop_constraint("ck_tickets_record_type", "tickets", type_="check")
    op.drop_column("tickets", "record_type")


def downgrade() -> None:
    bind = op.get_bind()

    op.add_column("tickets", sa.Column("record_type", sa.Text(), nullable=True))
    bind.execute(sa.text("""
        UPDATE tickets SET record_type = CASE
            WHEN (SELECT name FROM catalog_record_types c WHERE c.id = tickets.record_type_id) = 'Tarea'
            THEN 'task' ELSE 'ticket'
        END
    """))
    op.alter_column("tickets", "record_type", nullable=False, server_default="ticket")
    op.create_check_constraint("ck_tickets_record_type", "tickets", "record_type IN ('ticket','task')")

    op.drop_constraint("fk_tickets_record_type_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "record_type_id")
    op.drop_table("catalog_record_types")
