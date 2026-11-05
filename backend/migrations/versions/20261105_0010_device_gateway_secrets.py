"""Create encrypted gateway secret storage.

Revision ID: 20261105_0010
Revises: 20261105_0009
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261105_0010"
down_revision: Union[str, None] = "20261105_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_gateway_secrets",
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
            "secret_name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("key_version", sa.String(length=40), nullable=False),
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
        sa.PrimaryKeyConstraint(
            "workspace_id",
            "gateway_device_id",
            "secret_name",
            name="pk_device_gateway_secrets",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "gateway_device_id"],
            ["device_gateways.workspace_id", "device_gateways.device_id"],
            ondelete="CASCADE",
            name="fk_device_gateway_secrets_workspace_gateway",
        ),
    )


def downgrade() -> None:
    # Prevent concurrent inserts between the emptiness check and DROP TABLE.
    # PostgreSQL holds this lock until the migration transaction completes.
    op.execute(
        "LOCK TABLE device_gateway_secrets IN ACCESS EXCLUSIVE MODE"
    )

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM device_gateway_secrets) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: gateway secrets exist';
            END IF;
        END;
        $$;
    """)
    op.drop_table("device_gateway_secrets")
