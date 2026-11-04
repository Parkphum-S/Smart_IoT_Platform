"""Automation rule definitions and execution history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AutomationRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A workspace-scoped automation rule definition."""

    __tablename__ = "automation_rules"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_automation_rules_workspace_id_id"),
        ForeignKeyConstraint(["workspace_id", "created_by"], ["workspace_members.workspace_id", "workspace_members.user_id"], ondelete="RESTRICT", name="fk_automation_rules_workspace_creator"),
        Index("ix_automation_rules_workspace_enabled", "workspace_id", "is_enabled"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")


class AutomationCondition(UUIDPrimaryKeyMixin, Base):
    """A condition belonging to an automation rule."""

    __tablename__ = "automation_conditions"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "automation_rule_id"], ["automation_rules.workspace_id", "automation_rules.id"], ondelete="RESTRICT", name="fk_automation_conditions_workspace_rule"),
        Index("ix_automation_conditions_rule_order", "workspace_id", "automation_rule_id", "evaluation_order"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    automation_rule_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(80), nullable=False)
    condition_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    evaluation_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class AutomationAction(UUIDPrimaryKeyMixin, Base):
    """An action definition belonging to an automation rule."""

    __tablename__ = "automation_actions"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "automation_rule_id"], ["automation_rules.workspace_id", "automation_rules.id"], ondelete="RESTRICT", name="fk_automation_actions_workspace_rule"),
        Index("ix_automation_actions_rule_order", "workspace_id", "automation_rule_id", "execution_order"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    automation_rule_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    action_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class AutomationExecution(UUIDPrimaryKeyMixin, Base):
    """The recorded lifecycle and outcome of one automation run."""

    __tablename__ = "automation_executions"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "automation_rule_id"], ["automation_rules.workspace_id", "automation_rules.id"], ondelete="RESTRICT", name="fk_automation_executions_workspace_rule"),
        CheckConstraint("status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')", name="ck_automation_executions_status"),
        Index("ix_automation_executions_workspace_triggered", "workspace_id", "triggered_at"),
        Index("ix_automation_executions_rule_triggered", "automation_rule_id", "triggered_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    automation_rule_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
