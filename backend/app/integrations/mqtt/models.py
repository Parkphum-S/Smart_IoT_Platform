"""MQTT topic routing registry."""

from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MQTTTopicRoute(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """An exact MQTT topic route bound to one workspace device."""

    __tablename__ = "mqtt_topic_routes"

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "device_id"],
            ["devices.workspace_id", "devices.id"],
            ondelete="RESTRICT",
            name="fk_mqtt_topic_routes_workspace_device",
        ),
        UniqueConstraint(
            "broker_key",
            "topic",
            "direction",
            name="uq_mqtt_topic_routes_broker_topic_direction",
        ),
        CheckConstraint(
            "direction IN ('subscribe', 'publish')",
            name="ck_mqtt_topic_routes_direction",
        ),
        CheckConstraint(
            "qos BETWEEN 0 AND 2",
            name="ck_mqtt_topic_routes_qos",
        ),
        CheckConstraint(
            "length(trim(broker_key)) > 0",
            name="ck_mqtt_topic_routes_broker_key_nonempty",
        ),
        CheckConstraint(
            "length(trim(topic)) > 0 "
            "AND position('+' in topic) = 0 "
            "AND position('#' in topic) = 0",
            name="ck_mqtt_topic_routes_exact_topic",
        ),
        Index(
            "ix_mqtt_topic_routes_workspace_device",
            "workspace_id",
            "device_id",
            "is_enabled",
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    device_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    broker_key: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    topic: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    qos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
