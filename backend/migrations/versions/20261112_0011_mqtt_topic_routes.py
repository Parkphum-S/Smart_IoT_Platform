"""Create MQTT topic routing registry.

Revision ID: 20261112_0011
Revises: 20261105_0010
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261112_0011"
down_revision: Union[str, None] = "20261105_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mqtt_topic_routes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("broker_key", sa.String(80), nullable=False),
        sa.Column("topic", sa.String(512), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column(
            "qos",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_mqtt_topic_routes",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "device_id"],
            ["devices.workspace_id", "devices.id"],
            ondelete="RESTRICT",
            name="fk_mqtt_topic_routes_workspace_device",
        ),
        sa.UniqueConstraint(
            "broker_key",
            "topic",
            "direction",
            name="uq_mqtt_topic_routes_broker_topic_direction",
        ),
        sa.CheckConstraint(
            "direction IN ('subscribe', 'publish')",
            name="ck_mqtt_topic_routes_direction",
        ),
        sa.CheckConstraint(
            "qos BETWEEN 0 AND 2",
            name="ck_mqtt_topic_routes_qos",
        ),
        sa.CheckConstraint(
            "length(trim(broker_key)) > 0",
            name="ck_mqtt_topic_routes_broker_key_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(topic)) > 0 "
            "AND position('+' in topic) = 0 "
            "AND position('#' in topic) = 0",
            name="ck_mqtt_topic_routes_exact_topic",
        ),
    )

    op.create_index(
        "ix_mqtt_topic_routes_workspace_device",
        "mqtt_topic_routes",
        ["workspace_id", "device_id", "is_enabled"],
    )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE mqtt_topic_routes IN ACCESS EXCLUSIVE MODE"
    )

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM mqtt_topic_routes) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: MQTT topic routes exist';
            END IF;
        END;
        $$;
    """)

    op.drop_index(
        "ix_mqtt_topic_routes_workspace_device",
        table_name="mqtt_topic_routes",
    )

    op.drop_table("mqtt_topic_routes")
