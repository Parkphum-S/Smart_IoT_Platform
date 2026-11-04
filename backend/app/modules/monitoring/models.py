"""Monitoring events, alerts, notifications, and audit logs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceEvent(UUIDPrimaryKeyMixin, Base):
    """An event reported by a device."""

    __tablename__ = "device_events"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "device_id"], ["devices.workspace_id", "devices.id"], ondelete="RESTRICT", name="fk_device_events_workspace_device"),
        CheckConstraint("severity IN ('informational', 'warning', 'critical')", name="ck_device_events_severity"),
        Index("ix_device_events_workspace_occurred", "workspace_id", "occurred_at"),
        Index("ix_device_events_device_occurred", "device_id", "occurred_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AlertRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A workspace-scoped rule that defines when an alert should be raised."""

    __tablename__ = "alert_rules"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_alert_rules_workspace_id_id"),
        Index("ix_alert_rules_workspace_enabled", "workspace_id", "is_enabled"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    condition_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class Alert(UUIDPrimaryKeyMixin, Base):
    """An alert raised for a workspace, optionally linked to a rule and device."""

    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_alerts_workspace_id_id"),
        ForeignKeyConstraint(["workspace_id", "alert_rule_id"], ["alert_rules.workspace_id", "alert_rules.id"], ondelete="RESTRICT", name="fk_alerts_workspace_rule"),
        ForeignKeyConstraint(["workspace_id", "device_id"], ["devices.workspace_id", "devices.id"], ondelete="RESTRICT", name="fk_alerts_workspace_device"),
        CheckConstraint("severity IN ('informational', 'warning', 'critical')", name="ck_alerts_severity"),
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="ck_alerts_status"),
        Index("ix_alerts_workspace_status", "workspace_id", "status"),
        Index("ix_alerts_workspace_triggered", "workspace_id", "triggered_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    alert_rule_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    device_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", server_default="open")
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(UUIDPrimaryKeyMixin, Base):
    """A notification delivered to a workspace member."""

    __tablename__ = "notifications"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "user_id"], ["workspace_members.workspace_id", "workspace_members.user_id"], ondelete="RESTRICT", name="fk_notifications_workspace_member"),
        ForeignKeyConstraint(["workspace_id", "alert_id"], ["alerts.workspace_id", "alerts.id"], ondelete="RESTRICT", name="fk_notifications_workspace_alert"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_workspace_user_read", "workspace_id", "user_id", "read_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    alert_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """An append-oriented record of important platform actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_workspace_created", "workspace_id", "created_at"),
        Index("ix_audit_logs_actor_created", "actor_type", "actor_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    workspace_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
