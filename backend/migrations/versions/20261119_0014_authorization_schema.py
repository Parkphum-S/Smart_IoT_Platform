"""Create durable migration authorization and execution evidence tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261119_0014"
down_revision = "20261115_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "migration_authorization_states",
        sa.Column("manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("target_identity", sa.String(length=255), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("baseline_revision", sa.String(length=255), nullable=False),
        sa.Column("expected_revision", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'ISSUED'"),
            nullable=False,
        ),
        sa.Column("claimant_id", sa.String(length=255), nullable=True),
        sa.Column(
            "fencing_token",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "execution_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "outcome_details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('ISSUED', 'CLAIMED', 'EXECUTING', "
            "'SUCCEEDED', 'FAILED', 'UNKNOWN', 'EXPIRED')",
            name="ck_migration_authorization_status",
        ),
        sa.CheckConstraint(
            "operation IN ('MIGRATE', 'VERIFY', 'ROLLBACK')",
            name="ck_migration_authorization_operation",
        ),
        sa.CheckConstraint(
            "fencing_token >= 0",
            name="ck_migration_authorization_fencing_token",
        ),
        sa.CheckConstraint(
            "expires_at > issued_at",
            name="ck_migration_authorization_expiry",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_migration_authorization_claimant_status",
        "migration_authorization_states",
        ["claimant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_migration_authorization_digest",
        "migration_authorization_states",
        ["manifest_digest"],
        unique=False,
    )
    op.create_index(
        "ix_migration_authorization_status_expiry",
        "migration_authorization_states",
        ["status", "expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_migration_authorization_target_environment",
        "migration_authorization_states",
        ["target_identity", "environment"],
        unique=False,
    )

    op.create_table(
        "migration_target_states",
        sa.Column("target_identity", sa.String(length=255), nullable=False),
        sa.Column(
            "fencing_token",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "active_authorization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("active_claimant_id", sa.String(length=255), nullable=True),
        sa.Column(
            "lease_acquired_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "fencing_token >= 0",
            name="ck_migration_target_fencing_token",
        ),
        sa.CheckConstraint(
            "(active_authorization_id IS NULL AND "
            "active_claimant_id IS NULL) OR "
            "(active_authorization_id IS NOT NULL AND "
            "active_claimant_id IS NOT NULL)",
            name="ck_migration_target_active_claim",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "active_authorization_id",
            name="uq_migration_target_active_authorization",
        ),
        sa.UniqueConstraint("target_identity"),
        sa.ForeignKeyConstraint(
            ["active_authorization_id"],
            ["migration_authorization_states.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "migration_execution_evidence",
        sa.Column(
            "authorization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("target_identity", sa.String(length=255), nullable=False),
        sa.Column("claimant_id", sa.String(length=255), nullable=False),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column("execution_sequence", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("baseline_revision", sa.String(length=255), nullable=False),
        sa.Column("expected_revision", sa.String(length=255), nullable=False),
        sa.Column("observed_revision", sa.String(length=255), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "fencing_token > 0",
            name="ck_migration_execution_evidence_fencing",
        ),
        sa.CheckConstraint(
            "execution_sequence > 0",
            name="ck_migration_execution_evidence_sequence",
        ),
        sa.CheckConstraint(
            "evidence_type IN ('EXECUTION_STARTED', 'MIGRATION_RETURNED', "
            "'REVISION_VERIFIED', 'EXECUTION_COMMITTED', "
            "'EXECUTION_UNCERTAIN')",
            name="ck_migration_execution_evidence_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "authorization_id",
            "execution_sequence",
            name="uq_migration_execution_evidence_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["authorization_id"],
            ["migration_authorization_states.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_index(
        "ix_migration_execution_evidence_authorization_recorded",
        "migration_execution_evidence",
        ["authorization_id", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_migration_execution_evidence_target_recorded",
        "migration_execution_evidence",
        ["target_identity", "recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_migration_execution_evidence_target_recorded",
        table_name="migration_execution_evidence",
    )
    op.drop_index(
        "ix_migration_execution_evidence_authorization_recorded",
        table_name="migration_execution_evidence",
    )
    op.drop_table("migration_execution_evidence")

    op.drop_table("migration_target_states")

    op.drop_index(
        "ix_migration_authorization_target_environment",
        table_name="migration_authorization_states",
    )
    op.drop_index(
        "ix_migration_authorization_status_expiry",
        table_name="migration_authorization_states",
    )
    op.drop_index(
        "ix_migration_authorization_digest",
        table_name="migration_authorization_states",
    )
    op.drop_index(
        "ix_migration_authorization_claimant_status",
        table_name="migration_authorization_states",
    )
    op.drop_table("migration_authorization_states")
