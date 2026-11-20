"""Durable migration execution evidence ORM model."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    UUIDPrimaryKeyMixin,
)
from .authorization_models import (
    MigrationAuthorizationState,
)

# Importing the authorization model ensures its table is registered
# in the shared metadata before the evidence foreign key is resolved.
AUTHORIZATION_MODEL = MigrationAuthorizationState


EVIDENCE_TYPES = (
    "EXECUTION_STARTED",
    "MIGRATION_RETURNED",
    "REVISION_VERIFIED",
    "EXECUTION_COMMITTED",
    "EXECUTION_UNCERTAIN",
)


class MigrationExecutionEvidence(
    UUIDPrimaryKeyMixin,
    Base,
):
    """Append-only evidence associated with one authorization execution."""

    __tablename__ = "migration_execution_evidence"

    __table_args__ = (
        CheckConstraint(
            "fencing_token > 0",
            name="ck_migration_execution_evidence_fencing",
        ),
        CheckConstraint(
            "execution_sequence > 0",
            name="ck_migration_execution_evidence_sequence",
        ),
        CheckConstraint(
            "evidence_type IN ("
            "'EXECUTION_STARTED', "
            "'MIGRATION_RETURNED', "
            "'REVISION_VERIFIED', "
            "'EXECUTION_COMMITTED', "
            "'EXECUTION_UNCERTAIN'"
            ")",
            name="ck_migration_execution_evidence_type",
        ),
        UniqueConstraint(
            "authorization_id",
            "execution_sequence",
            name="uq_migration_execution_evidence_sequence",
        ),
        Index(
            "ix_migration_execution_evidence_authorization_recorded",
            "authorization_id",
            "recorded_at",
        ),
        Index(
            "ix_migration_execution_evidence_target_recorded",
            "target_identity",
            "recorded_at",
        ),
    )

    authorization_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "migration_authorization_states.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    target_identity: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    claimant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    fencing_token: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    execution_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(40),
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
    observed_revision: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.clock_timestamp(),
    )
