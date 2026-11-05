"""Create device gateway membership table.

Revision ID: 20261105_0009
Revises: 20261105_0008
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261105_0009"
down_revision: Union[str, None] = "20261105_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_gateway_members",
        sa.Column(
            "child_device_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gateway_device_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "child_device_id",
            name="pk_device_gateway_members",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "child_device_id"],
            ["devices.workspace_id", "devices.id"],
            ondelete="RESTRICT",
            name="fk_device_gateway_members_workspace_child",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "gateway_device_id"],
            ["device_gateways.workspace_id", "device_gateways.device_id"],
            ondelete="RESTRICT",
            name="fk_device_gateway_members_workspace_gateway",
        ),
        sa.CheckConstraint(
            "child_device_id <> gateway_device_id",
            name="ck_device_gateway_members_not_self",
        ),
    )

    op.create_index(
        "ix_device_gateway_members_gateway_device_id",
        "device_gateway_members",
        ["gateway_device_id"],
        unique=False,
    )


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM device_gateway_members) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: gateway membership data exists';
            END IF;
        END;
        $$;
    """)
    op.drop_index(
        "ix_device_gateway_members_gateway_device_id",
        table_name="device_gateway_members",
    )
    op.drop_table("device_gateway_members")
