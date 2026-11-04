"""Telemetry metric definitions and device readings."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin


class TelemetryMetric(UUIDPrimaryKeyMixin, Base):
    """A metric supported by a particular device type."""

    __tablename__ = "telemetry_metrics"
    __table_args__ = (
        UniqueConstraint("device_type_id", "metric_key", name="uq_telemetry_metrics_device_type_key"),
        UniqueConstraint("device_type_id", "id", name="uq_telemetry_metrics_device_type_id"),
        CheckConstraint("data_type IN ('numeric', 'text', 'boolean', 'json')", name="ck_telemetry_metrics_data_type"),
        Index("ix_telemetry_metrics_device_type_id", "device_type_id"),
    )

    device_type_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("device_types.id", ondelete="RESTRICT"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TelemetryReading(UUIDPrimaryKeyMixin, Base):
    """A timestamped metric value reported by a device."""

    __tablename__ = "telemetry_readings"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "device_id"], ["devices.workspace_id", "devices.id"], ondelete="RESTRICT", name="fk_telemetry_readings_workspace_device"),
        ForeignKeyConstraint(["device_id", "device_type_id"], ["devices.id", "devices.device_type_id"], ondelete="RESTRICT", name="fk_telemetry_readings_device_type"),
        ForeignKeyConstraint(["device_type_id", "metric_id"], ["telemetry_metrics.device_type_id", "telemetry_metrics.id"], ondelete="RESTRICT", name="fk_telemetry_readings_device_type_metric"),
        CheckConstraint("num_nonnulls(value_numeric, value_text, value_boolean, value_json) = 1", name="ck_telemetry_readings_exactly_one_value"),
        Index("ix_telemetry_readings_device_recorded", "device_id", "recorded_at"),
        Index("ix_telemetry_readings_workspace_recorded", "workspace_id", "recorded_at"),
        Index("ix_telemetry_readings_metric_recorded", "metric_id", "recorded_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    device_type_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    metric_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    quality: Mapped[str | None] = mapped_column(String(30), nullable=True)
