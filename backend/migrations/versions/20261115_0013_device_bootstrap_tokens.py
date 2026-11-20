"""Create device-bound single-use bootstrap tokens.

Revision ID: 20261115_0013
Revises: 20261112_0012
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261115_0013"
down_revision = "20261112_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_bootstrap_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "consumed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_device_bootstrap_tokens",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "device_id"],
            ["devices.workspace_id", "devices.id"],
            ondelete="RESTRICT",
            name="fk_device_bootstrap_tokens_workspace_device",
        ),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_device_bootstrap_tokens_token_hash",
        ),
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'",
            name="ck_device_bootstrap_tokens_hash_format",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_device_bootstrap_tokens_expiry",
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name="ck_device_bootstrap_tokens_consumed_time",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_device_bootstrap_tokens_revoked_time",
        ),
        sa.CheckConstraint(
            "NOT (consumed_at IS NOT NULL AND revoked_at IS NOT NULL)",
            name="ck_device_bootstrap_tokens_terminal_state",
        ),
    )

    op.create_index(
        "ix_device_bootstrap_tokens_workspace_device",
        "device_bootstrap_tokens",
        ["workspace_id", "device_id", "created_at"],
    )

    op.create_index(
        "ix_device_bootstrap_tokens_expires_at",
        "device_bootstrap_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE device_bootstrap_tokens IN ACCESS EXCLUSIVE MODE"
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM device_bootstrap_tokens) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: device bootstrap tokens exist';
            END IF;
        END;
        $$;
        """
    )

    op.drop_index(
        "ix_device_bootstrap_tokens_expires_at",
        table_name="device_bootstrap_tokens",
    )

    op.drop_index(
        "ix_device_bootstrap_tokens_workspace_device",
        table_name="device_bootstrap_tokens",
    )

    op.drop_table("device_bootstrap_tokens")
