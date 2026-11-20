"""Add broker-scoped identity and integrity constraints to device credentials.

Revision ID: 20261112_0012
Revises: 20261112_0011
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261112_0012"
down_revision = "20261112_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fail closed: existing credentials need an explicit broker identity mapping.
    op.execute(
        "LOCK TABLE device_credentials IN ACCESS EXCLUSIVE MODE"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM device_credentials) THEN
                RAISE EXCEPTION
                    'Cannot migrate device_credentials: existing rows require explicit broker identity mapping';
            END IF;
        END;
        $$;
        """
    )

    op.add_column(
        "device_credentials",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "device_credentials",
        sa.Column("broker_key", sa.String(length=80), nullable=False),
    )
    op.add_column(
        "device_credentials",
        sa.Column(
            "credential_identifier",
            sa.String(length=160),
            nullable=False,
        ),
    )

    op.drop_constraint(
        "device_credentials_device_id_fkey",
        "device_credentials",
        type_="foreignkey",
    )

    op.execute(
        """
        ALTER TABLE device_credentials
        RENAME CONSTRAINT device_credentials_pkey
        TO pk_device_credentials
        """
    )

    op.alter_column(
        "device_credentials",
        "credential_status",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="pending",
    )

    op.create_foreign_key(
        "fk_device_credentials_workspace_device",
        "device_credentials",
        "devices",
        ["workspace_id", "device_id"],
        ["workspace_id", "id"],
        ondelete="RESTRICT",
    )

    op.create_unique_constraint(
        "uq_device_credentials_broker_identifier",
        "device_credentials",
        ["broker_key", "credential_identifier"],
    )

    op.create_check_constraint(
        "ck_device_credentials_broker_key_nonempty",
        "device_credentials",
        "length(btrim(broker_key)) > 0",
    )
    op.create_check_constraint(
        "ck_device_credentials_identifier_nonempty",
        "device_credentials",
        "length(btrim(credential_identifier)) > 0",
    )
    op.create_check_constraint(
        "ck_device_credentials_type_nonempty",
        "device_credentials",
        "length(btrim(credential_type)) > 0",
    )
    op.create_check_constraint(
        "ck_device_credentials_exactly_one_secret",
        "device_credentials",
        """
        (NULLIF(btrim(secret_hash), '') IS NOT NULL)
        <> (NULLIF(btrim(secret_reference), '') IS NOT NULL)
        """,
    )
    op.create_check_constraint(
        "ck_device_credentials_status",
        "device_credentials",
        "credential_status IN ('pending', 'active', 'revoked')",
    )
    op.create_check_constraint(
        "ck_device_credentials_expiry_after_creation",
        "device_credentials",
        "expires_at IS NULL OR expires_at > created_at",
    )
    op.create_check_constraint(
        "ck_device_credentials_revocation_consistency",
        "device_credentials",
        """
        (credential_status = 'revoked') = (revoked_at IS NOT NULL)
        """,
    )

    op.create_index(
        "ix_device_credentials_workspace_device_status",
        "device_credentials",
        ["workspace_id", "device_id", "credential_status"],
    )


def downgrade() -> None:
    # Do not discard broker identity or credential metadata.
    op.execute(
        "LOCK TABLE device_credentials IN ACCESS EXCLUSIVE MODE"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM device_credentials) THEN
                RAISE EXCEPTION
                    'Cannot downgrade device_credentials: rows contain broker identity data';
            END IF;
        END;
        $$;
        """
    )

    op.drop_index(
        "ix_device_credentials_workspace_device_status",
        table_name="device_credentials",
    )

    op.drop_constraint(
        "ck_device_credentials_revocation_consistency",
        "device_credentials",
        type_="check",
    )
    op.drop_constraint(
        "ck_device_credentials_expiry_after_creation",
        "device_credentials",
        type_="check",
    )
    op.drop_constraint(
        "ck_device_credentials_status",
        "device_credentials",
        type_="check",
    )
    op.drop_constraint(
        "ck_device_credentials_exactly_one_secret",
        "device_credentials",
        type_="check",
    )
    op.drop_constraint(
        "ck_device_credentials_type_nonempty",
        "device_credentials",
        type_="check",
    )
    op.drop_constraint(
        "ck_device_credentials_identifier_nonempty",
        "device_credentials",
        type_="check",
    )
    op.drop_constraint(
        "ck_device_credentials_broker_key_nonempty",
        "device_credentials",
        type_="check",
    )

    op.drop_constraint(
        "uq_device_credentials_broker_identifier",
        "device_credentials",
        type_="unique",
    )
    op.drop_constraint(
        "fk_device_credentials_workspace_device",
        "device_credentials",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "device_credentials_device_id_fkey",
        "device_credentials",
        "devices",
        ["device_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        """
        ALTER TABLE device_credentials
        RENAME CONSTRAINT pk_device_credentials
        TO device_credentials_pkey
        """
    )

    op.alter_column(
        "device_credentials",
        "credential_status",
        existing_type=sa.String(length=20),
        nullable=True,
        server_default=None,
    )

    op.drop_column("device_credentials", "credential_identifier")
    op.drop_column("device_credentials", "broker_key")
    op.drop_column("device_credentials", "workspace_id")
