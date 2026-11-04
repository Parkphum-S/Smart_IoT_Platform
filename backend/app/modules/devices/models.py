"""Device, room, and device group SQLAlchemy models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A supported device type and its declared capabilities."""

    __tablename__ = "device_types"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical or virtual device registered to a workspace."""

    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_devices_workspace_id_id"),
        UniqueConstraint("id", "device_type_id", name="uq_devices_id_device_type"),
        UniqueConstraint("device_uid", name="uq_devices_device_uid"),
        Index("ix_devices_workspace_enabled", "workspace_id", "is_enabled"),
        Index("ix_devices_device_type_id", "device_type_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    device_type_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("device_types.id", ondelete="RESTRICT"), nullable=False)
    device_uid: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    protocol: Mapped[str] = mapped_column(String(40), nullable=False, default="mqtt", server_default="mqtt")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class DeviceCredential(UUIDPrimaryKeyMixin, Base):
    """A device authentication credential or external secret reference."""

    __tablename__ = "device_credentials"
    __table_args__ = (
        Index("ix_device_credentials_device_id", "device_id"),
    )

    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(40), nullable=False)
    secret_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secret_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceStatus(Base):
    """Latest reported connection and state information for a device."""

    __tablename__ = "device_status"
    __table_args__ = (
        CheckConstraint("connection_state IN ('online', 'offline', 'unknown')", name="ck_device_status_connection_state"),
    )

    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), primary_key=True)
    connection_state: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown", server_default="unknown")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named physical area within a workspace."""

    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_rooms_workspace_id_id"),
        Index("ix_rooms_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class DeviceRoom(Base):
    """Assign a device to at most one room within the same workspace."""

    __tablename__ = "device_rooms"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "device_id"], ["devices.workspace_id", "devices.id"], ondelete="RESTRICT", name="fk_device_rooms_workspace_device"),
        ForeignKeyConstraint(["workspace_id", "room_id"], ["rooms.workspace_id", "rooms.id"], ondelete="RESTRICT", name="fk_device_rooms_workspace_room"),
        Index("ix_device_rooms_workspace_room", "workspace_id", "room_id"),
        Index("ix_device_rooms_workspace_device", "workspace_id", "device_id"),
    )

    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    room_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DeviceGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-defined collection of devices in a workspace."""

    __tablename__ = "device_groups"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_device_groups_workspace_id_id"),
        Index("ix_device_groups_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeviceGroupMember(Base):
    """Membership of a device in a workspace-scoped device group."""

    __tablename__ = "device_group_members"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "device_group_id"], ["device_groups.workspace_id", "device_groups.id"], ondelete="RESTRICT", name="fk_device_group_members_workspace_group"),
        ForeignKeyConstraint(["workspace_id", "device_id"], ["devices.workspace_id", "devices.id"], ondelete="RESTRICT", name="fk_device_group_members_workspace_device"),
        Index("ix_device_group_members_workspace_device", "workspace_id", "device_id"),
        Index("ix_device_group_members_workspace_group", "workspace_id", "device_group_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    device_group_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
