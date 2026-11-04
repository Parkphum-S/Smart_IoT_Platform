"""User and workspace SQLAlchemy models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform user account."""

    __tablename__ = "users"
    __table_args__ = (
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Independently managed home, building, or site."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC", server_default="UTC")


class WorkspaceMember(UUIDPrimaryKeyMixin, Base):
    """User membership and role within a workspace."""

    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_user"),
        CheckConstraint("role IN ('owner', 'admin', 'operator', 'viewer')", name="ck_workspace_members_role"),
        Index("ix_workspace_members_user_active", "user_id", "is_active"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserSession(UUIDPrimaryKeyMixin, Base):
    """Server-side session associated with a platform user."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_user_sessions_expiry_after_creation",
        ),
        Index("ix_user_sessions_user_expires", "user_id", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class MembershipHistory(UUIDPrimaryKeyMixin, Base):
    """Permanent, append-only record of workspace membership changes."""

    __tablename__ = "membership_history"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'role_changed', 'deactivated', "
            "'reactivated', 'ownership_transferred')",
            name="ck_membership_history_event_type",
        ),
        CheckConstraint(
            "previous_role IS NULL OR previous_role IN "
            "('owner', 'admin', 'operator', 'viewer')",
            name="ck_membership_history_previous_role",
        ),
        CheckConstraint(
            "new_role IS NULL OR new_role IN "
            "('owner', 'admin', 'operator', 'viewer')",
            name="ck_membership_history_new_role",
        ),
        Index("ix_membership_history_workspace_created", "workspace_id", "created_at"),
        Index("ix_membership_history_membership_created", "membership_id", "created_at"),
        Index("ix_membership_history_membership_sequence", "membership_id", "event_sequence"),
        Index("ix_membership_history_actor_created", "actor_id", "created_at"),
        Index("ix_membership_history_subject_created", "subject_user_id", "created_at"),
    )

    event_sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    subject_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
