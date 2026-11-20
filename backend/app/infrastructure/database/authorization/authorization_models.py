"""SQLAlchemy models for migration authorization state."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
)


class MigrationAuthorizationState(
    UUIDPrimaryKeyMixin,
    Base,
):
    """Persisted lifecycle state of an authorized migration."""

    __tablename__ = "migration_authorization_states"

    __table_args__ = (
        CheckConstraint(
            "status IN ('ISSUED', 'CLAIMED', 'EXECUTING', "
            "'SUCCEEDED', 'FAILED', 'UNKNOWN', 'EXPIRED')",
            name="ck_migration_authorization_status",
        ),
        CheckConstraint(
            "operation IN ('MIGRATE', 'VERIFY', 'ROLLBACK')",
            name="ck_migration_authorization_operation",
        ),
        CheckConstraint(
            "fencing_token >= 0",
            name="ck_migration_authorization_fencing_token",
        ),
        CheckConstraint(
            "expires_at > issued_at",
            name="ck_migration_authorization_expiry",
        ),
        Index(
            "ix_migration_authorization_status_expiry",
            "status",
            "expires_at",
        ),
        Index(
            "ix_migration_authorization_claimant_status",
            "claimant_id",
            "status",
        ),
        Index(
            "ix_migration_authorization_digest",
            "manifest_digest",
        ),
        Index(
            "ix_migration_authorization_target_environment",
            "target_identity",
            "environment",
        ),
    )

    manifest_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    target_identity: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    environment: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    baseline_revision: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    expected_revision: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ISSUED'"),
    )
    claimant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    fencing_token: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    execution_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    outcome_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class MigrationTargetState(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """Persist target-scoped migration lock and fencing state."""

    __tablename__ = "migration_target_states"

    __table_args__ = (
        CheckConstraint(
            "fencing_token >= 0",
            name="ck_migration_target_fencing_token",
        ),
        CheckConstraint(
            "(active_authorization_id IS NULL "
            "AND active_claimant_id IS NULL) OR "
            "(active_authorization_id IS NOT NULL "
            "AND active_claimant_id IS NOT NULL)",
            name="ck_migration_target_active_claim",
        ),
        UniqueConstraint(
            "active_authorization_id",
            name="uq_migration_target_active_authorization",
        ),
    )

    target_identity: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    fencing_token: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    active_authorization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "migration_authorization_states.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    active_claimant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    lease_acquired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
