"""Persistence operations for workspace-scoped MQTT topic routes."""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mqtt.models import MQTTTopicRoute
from app.modules.devices.models import Device


class MQTTTopicRouteRepository:
    """Query MQTT routes without owning the caller's transaction."""

    @staticmethod
    def _active_device_statement():
        return select(MQTTTopicRoute).join(
            Device,
            and_(
                Device.id == MQTTTopicRoute.device_id,
                Device.workspace_id == MQTTTopicRoute.workspace_id,
            ),
        ).where(
            MQTTTopicRoute.is_enabled.is_(True),
            Device.is_enabled.is_(True),
            Device.lifecycle_status == "active",
        )

    @staticmethod
    async def get_ingress_route(
        session: AsyncSession,
        *,
        broker_key: str,
        topic: str,
    ) -> MQTTTopicRoute | None:
        """Find an enabled backend-subscription route."""
        statement = (
            MQTTTopicRouteRepository._active_device_statement()
            .where(
                MQTTTopicRoute.broker_key == broker_key,
                MQTTTopicRoute.topic == topic,
                MQTTTopicRoute.direction == "subscribe",
            )
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_egress_route(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
        broker_key: str,
        topic: str,
    ) -> MQTTTopicRoute | None:
        """Find an enabled backend-publication route within a workspace."""
        statement = (
            MQTTTopicRouteRepository._active_device_statement()
            .where(
                MQTTTopicRoute.workspace_id == workspace_id,
                MQTTTopicRoute.device_id == device_id,
                MQTTTopicRoute.broker_key == broker_key,
                MQTTTopicRoute.topic == topic,
                MQTTTopicRoute.direction == "publish",
            )
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_enabled_routes(
        session: AsyncSession,
        *,
        broker_key: str,
        direction: str,
    ) -> list[MQTTTopicRoute]:
        """List enabled routes for active devices in deterministic order."""
        if direction not in {"subscribe", "publish"}:
            raise ValueError("Invalid MQTT route direction.")

        statement = (
            MQTTTopicRouteRepository._active_device_statement()
            .where(
                MQTTTopicRoute.broker_key == broker_key,
                MQTTTopicRoute.direction == direction,
            )
            .order_by(MQTTTopicRoute.topic, MQTTTopicRoute.id)
        )
        result = await session.execute(statement)
        return list(result.scalars().all())
