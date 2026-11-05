"""Create device gateway configuration table.

Revision ID: 20261105_0008
Revises: 20261105_0007
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261105_0008"
down_revision: Union[str, None] = "20261105_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_gateways",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gateway_type", sa.String(length=40), nullable=False),
        sa.Column("adapter_key", sa.String(length=120), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("device_id", name="pk_device_gateways"),
        sa.UniqueConstraint(
            "workspace_id",
            "device_id",
            name="uq_device_gateways_workspace_device",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            ondelete="RESTRICT",
            name="fk_device_gateways_device",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "device_id"],
            ["devices.workspace_id", "devices.id"],
            ondelete="RESTRICT",
            name="fk_device_gateways_workspace_device",
        ),
    )


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM device_gateways) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: gateway configuration data exists';
            END IF;
        END;
        $$;
    """)
    op.drop_table("device_gateways")
