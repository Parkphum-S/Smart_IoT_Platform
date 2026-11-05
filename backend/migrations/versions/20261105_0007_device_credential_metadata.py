"""Add staged device credential metadata.

Revision ID: 20261105_0007
Revises: 20261105_0006
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261105_0007"
down_revision: Union[str, None] = "20261105_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "device_credentials",
        sa.Column("credential_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "device_credentials",
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "device_credentials",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM device_credentials
                WHERE credential_status IS NOT NULL
                   OR rotated_at IS NOT NULL
                   OR last_used_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: credential metadata exists';
            END IF;
        END;
        $$;
    """)
    op.drop_column("device_credentials", "last_used_at")
    op.drop_column("device_credentials", "rotated_at")
    op.drop_column("device_credentials", "credential_status")
