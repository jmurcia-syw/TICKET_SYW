"""task_lists + subtareas + reversión del ciclo de vida de Tarea a los 10 estados de Ticket

Revision ID: 024
Revises: 023
Create Date: 2026-07-08

Revierte las Decisiones 1 y 2 de la spec 008 (spec 009): la Tarea deja de tener un catálogo de
4 estados propio y una columna `list_name` de texto libre. Migración de datos incluida —
ver research.md Decisión 4 de la spec 009. NO es trivialmente reversible: `downgrade()` restaura
el esquema pero no puede reconstruir qué Tarea estaba en "pendiente" vs "en_progreso" una vez
colapsadas a "nuevo"/"en_ejecucion".
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

OLD_STATUSES = (
    "nuevo", "pre_analisis", "contacto", "en_analisis", "en_ejecucion",
    "en_pruebas", "pendiente_usuario", "resuelto", "cerrado", "cancelado",
)
SPEC_008_STATUSES = OLD_STATUSES + ("pendiente", "en_progreso", "hecha")


def upgrade() -> None:
    op.create_table(
        "task_lists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_task_lists_project_id", "task_lists", ["project_id"])

    op.add_column("tickets", sa.Column("list_id", UUID(as_uuid=True), sa.ForeignKey("task_lists.id"), nullable=True))
    op.add_column("tickets", sa.Column("parent_task_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id"), nullable=True))
    op.create_index("ix_tickets_parent_task_id", "tickets", ["parent_task_id"])

    # ── Backfill: list_name (texto libre, spec 008) → task_lists (entidad real, spec 009) ──
    op.execute("""
        INSERT INTO task_lists (id, project_id, name, position, created_at, updated_at)
        SELECT gen_random_uuid(), t.project_id, t.list_name, 0, now(), now()
        FROM (
            SELECT DISTINCT project_id, list_name FROM tickets
            WHERE list_name IS NOT NULL AND project_id IS NOT NULL
              AND record_type_id = (SELECT id FROM catalog_record_types WHERE name = 'Tarea')
        ) t
    """)
    op.execute("""
        UPDATE tickets SET list_id = tl.id
        FROM task_lists tl
        WHERE tickets.list_name = tl.name AND tickets.project_id = tl.project_id
          AND tickets.record_type_id = (SELECT id FROM catalog_record_types WHERE name = 'Tarea')
    """)

    # ── Backfill: estados de 4 valores (spec 008) → catálogo de 10 de Ticket (spec 009) ──
    op.execute("""
        UPDATE tickets SET status = CASE status
            WHEN 'pendiente' THEN 'nuevo'
            WHEN 'en_progreso' THEN 'en_ejecucion'
            WHEN 'hecha' THEN 'cerrado'
            ELSE status
        END
        WHERE record_type_id = (SELECT id FROM catalog_record_types WHERE name = 'Tarea')
          AND status IN ('pendiente', 'en_progreso', 'hecha')
    """)

    op.drop_constraint("ck_tickets_status", "tickets", type_="check")
    status_check = ", ".join(f"'{s}'" for s in OLD_STATUSES)
    op.create_check_constraint("ck_tickets_status", "tickets", f"status IN ({status_check})")


def downgrade() -> None:
    op.drop_constraint("ck_tickets_status", "tickets", type_="check")
    status_check = ", ".join(f"'{s}'" for s in SPEC_008_STATUSES)
    op.create_check_constraint("ck_tickets_status", "tickets", f"status IN ({status_check})")

    op.drop_index("ix_tickets_parent_task_id", table_name="tickets")
    op.drop_column("tickets", "parent_task_id")
    op.drop_column("tickets", "list_id")
    op.drop_index("ix_task_lists_project_id", table_name="task_lists")
    op.drop_table("task_lists")
