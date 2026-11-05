"""Application service for gateway registration and membership."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import (
    Device,
    DeviceGateway,
    DeviceGatewayMember,
)
from app.modules.devices.services.audit_repository import DeviceAuditRepository
from app.modules.devices.services.device_repository import DeviceRepository
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    GatewayAlreadyRegistered,
    GatewayCycleDetected,
    GatewayMembershipConflict,
    GatewayNotFound,
)
from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import Permission


class GatewayService:
    """Gateway business rules; transaction is controlled by the caller."""

    def __init__(self) -> None:
        self.repository = DeviceRepository()
        self.audit = DeviceAuditRepository()
        self.authorization = AuthorizationService()

    async def _authorize(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        permission: Permission,
    ) -> None:
        try:
            await self.authorization.authorize(
                session,
                user_id=actor_id,
                workspace_id=workspace_id,
                permission=permission.value,
            )
        except (WorkspaceMembershipNotFound, PermissionDenied):
            raise DevicePermissionDenied from None

    async def register_gateway(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
        gateway_type: str,
        adapter_key: str,
        configuration: dict | None = None,
    ) -> DeviceGateway:
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_CREATE,
        )
        device = await self.repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            for_update=True,
        )
        if device is None:
            raise DeviceNotFound

        existing = await session.get(DeviceGateway, device_id)
        if existing is not None:
            raise GatewayAlreadyRegistered

        if not isinstance(gateway_type, str) or not isinstance(adapter_key, str):
            raise DeviceInvalidInput("Gateway type and adapter key must be strings.")
        gateway_type = gateway_type.strip().lower()
        adapter_key = adapter_key.strip()
        if not gateway_type or len(gateway_type) > 40:
            raise DeviceInvalidInput("Invalid gateway type.")
        if not adapter_key or len(adapter_key) > 120:
            raise DeviceInvalidInput("Invalid adapter key.")
        if configuration is not None and not isinstance(configuration, dict):
            raise DeviceInvalidInput("Gateway configuration must be an object.")

        gateway = DeviceGateway(
            device_id=device_id,
            workspace_id=workspace_id,
            gateway_type=gateway_type,
            adapter_key=adapter_key,
            configuration=configuration or {},
        )
        session.add(gateway)
        await session.flush()
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway.registered",
            resource_type="device_gateway",
            resource_id=device_id,
            details={
                "gateway_type": gateway_type,
                "adapter_key": adapter_key,
            },
        )
        return gateway

    async def update_gateway(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
        gateway_type: str | None = None,
        adapter_key: str | None = None,
        configuration: dict | None = None,
    ) -> DeviceGateway:
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        gateway = await session.get(DeviceGateway, device_id)
        if gateway is None or gateway.workspace_id != workspace_id:
            raise GatewayNotFound

        changed = []
        if gateway_type is not None:
            if not isinstance(gateway_type, str):
                raise DeviceInvalidInput("Invalid gateway type.")
            value = gateway_type.strip().lower()
            if not value or len(value) > 40:
                raise DeviceInvalidInput("Invalid gateway type.")
            gateway.gateway_type = value
            changed.append("gateway_type")
        if adapter_key is not None:
            if not isinstance(adapter_key, str):
                raise DeviceInvalidInput("Invalid adapter key.")
            value = adapter_key.strip()
            if not value or len(value) > 120:
                raise DeviceInvalidInput("Invalid adapter key.")
            gateway.adapter_key = value
            changed.append("adapter_key")
        if configuration is not None:
            if not isinstance(configuration, dict):
                raise DeviceInvalidInput("Gateway configuration must be an object.")
            gateway.configuration = configuration
            changed.append("configuration")
        if not changed:
            raise GatewayMembershipConflict("At least one field must be supplied.")

        await session.flush()
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway.updated",
            resource_type="device_gateway",
            resource_id=device_id,
            details={"changed_fields": sorted(changed)},
        )
        return gateway

    async def _would_create_cycle(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        child_device_id: UUID,
        gateway_device_id: UUID,
    ) -> bool:
        cursor = gateway_device_id
        visited: set[UUID] = set()
        while cursor not in visited:
            if cursor == child_device_id:
                return True
            visited.add(cursor)
            result = await session.execute(
                select(DeviceGatewayMember.gateway_device_id).where(
                    DeviceGatewayMember.workspace_id == workspace_id,
                    DeviceGatewayMember.child_device_id == cursor,
                )
            )
            parent = result.scalar_one_or_none()
            if parent is None:
                return False
            cursor = parent
        return True

    async def assign_gateway(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        child_device_id: UUID,
        gateway_device_id: UUID,
    ) -> DeviceGatewayMember:
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        if child_device_id == gateway_device_id:
            raise GatewayCycleDetected

        child = await self.repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=child_device_id,
            for_update=True,
        )
        if child is None:
            raise DeviceNotFound
        gateway = await session.get(DeviceGateway, gateway_device_id)
        if gateway is None or gateway.workspace_id != workspace_id:
            raise GatewayNotFound

        existing = await session.get(DeviceGatewayMember, child_device_id)
        if existing is not None:
            raise GatewayMembershipConflict(
                "The child device already has a primary gateway."
            )

        if await self._would_create_cycle(
            session,
            workspace_id=workspace_id,
            child_device_id=child_device_id,
            gateway_device_id=gateway_device_id,
        ):
            raise GatewayCycleDetected

        membership = DeviceGatewayMember(
            child_device_id=child_device_id,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
        )
        session.add(membership)
        await session.flush()
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway_member.assigned",
            resource_type="device_gateway_member",
            resource_id=child_device_id,
            details={"gateway_device_id": str(gateway_device_id)},
        )
        return membership

    async def remove_gateway(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        child_device_id: UUID,
    ) -> None:
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        membership = await session.get(DeviceGatewayMember, child_device_id)
        if membership is None or membership.workspace_id != workspace_id:
            raise GatewayMembershipConflict("Gateway membership not found.")

        gateway_device_id = membership.gateway_device_id
        await session.delete(membership)
        await session.flush()
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway_member.removed",
            resource_type="device_gateway_member",
            resource_id=child_device_id,
            details={"gateway_device_id": str(gateway_device_id)},
        )
