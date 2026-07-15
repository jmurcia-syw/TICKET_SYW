"""Accesos y conexiones múltiples del Cliente (spec 018)

Revision ID: 030
Revises: 029
Create Date: 2026-07-15

Crea `client_access` (VPN/URL de sistema/Escritorio remoto, 1-a-muchos con `clients`) y
`client_access_attachments`, y migra sin pérdida los datos ya cargados en las columnas legacy
`clients.vpn_ips`/`clients.vpn_credentials` hacia un registro `client_access` inicial tipo
`vpn` (data-model.md, "Notas de migración"). Esas dos columnas legacy NO se eliminan aquí —
quedan sin uso en la API/UI nueva (retirarlas es un cambio separado, fuera de alcance de este
spec, UAT OBS-0001/OBS-0008/OBS-0017).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_access",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("access_type", sa.Text(), nullable=False),
        sa.Column("environment", sa.Text(), nullable=True),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("password", sa.LargeBinary(), nullable=True),
        sa.Column("host", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_check_constraint(
        "ck_client_access_type", "client_access",
        "access_type IN ('vpn','system_url','remote_desktop')")
    op.create_check_constraint(
        "ck_client_access_environment", "client_access",
        "environment IS NULL OR environment IN ('dev','test','prod')")

    op.create_table(
        "client_access_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Data migration: un client_access inicial tipo 'vpn' por cada cliente que ya tuviera algo
    # cargado en vpn_ips/vpn_credentials (sin pérdida, FR-007/FR-008/SC-004).
    bind = op.get_bind()
    bind.execute(sa.text(
        """
        INSERT INTO client_access (id, client_id, access_type, host, password, created_at, updated_at)
        SELECT gen_random_uuid(), id, 'vpn', convert_from(vpn_ips, 'UTF8'), vpn_credentials, now(), now()
        FROM clients
        WHERE vpn_ips IS NOT NULL OR vpn_credentials IS NOT NULL
        """
    ))


def downgrade() -> None:
    bind = op.get_bind()
    # Reconstruye vpn_ips/vpn_credentials desde el client_access 'vpn' más antiguo de cada
    # cliente (best-effort: si un cliente acumuló más de un acceso VPN, se preserva solo el
    # primero — limitación documentada en data-model.md).
    bind.execute(sa.text(
        """
        UPDATE clients c
        SET vpn_ips = sub.host_bytes, vpn_credentials = sub.password
        FROM (
            SELECT DISTINCT ON (client_id) client_id,
                   convert_to(host, 'UTF8') AS host_bytes, password
            FROM client_access
            WHERE access_type = 'vpn'
            ORDER BY client_id, created_at ASC
        ) sub
        WHERE c.id = sub.client_id
        """
    ))
    op.drop_table("client_access_attachments")
    op.drop_constraint("ck_client_access_environment", "client_access", type_="check")
    op.drop_constraint("ck_client_access_type", "client_access", type_="check")
    op.drop_table("client_access")
