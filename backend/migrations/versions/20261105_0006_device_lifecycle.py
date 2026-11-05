"""Add staged device lifecycle metadata.

Revision ID: 20261105_0006
Revises: 20261104_0005
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261105_0006"
down_revision: Union[str, None] = "20261104_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("lifecycle_status", sa.String(length=40), nullable=True),
    )
    op.create_index(
        "ix_devices_workspace_lifecycle_status",
        "devices",
        ["workspace_id", "lifecycle_status"],
        unique=False,
    )


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM devices
                WHERE lifecycle_status IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: device lifecycle data exists';
            END IF;
        END;
        $$;
    """)
    op.drop_index(
        "ix_devices_workspace_lifecycle_status",
        table_name="devices",
    )
    op.drop_column("devices", "lifecycle_status")
