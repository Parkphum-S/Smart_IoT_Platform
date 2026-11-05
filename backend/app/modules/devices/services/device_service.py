"""Application service for workspace device management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import Device
from app.modules.devices.services.audit_repository import DeviceAuditRepository
from app.modules.devices.services.device_repository import DeviceRepository
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    DeviceStateConflict,
    DeviceTypeNotFound,
)
from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import Permission


LIFECYCLE_TRANSITIONS = {
    "pending_provisioning": {"active", "disabled"},
    "active": {"disabled", "revoked"},
    "disabled": {"active", "revoked", "retired"},
    "revoked": {"retired"},
    "retired": set(),
}

LIFECYCLE_VALUES = frozenset(LIFECYCLE_TRANSITIONS)


class DeviceService:
    """Device business rules; never commits the caller's transaction."""

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

    @staticmethod
    def _normalize_protocol(value: str) -> str:
        if not isinstance(value, str):
            raise DeviceInvalidInput("Invalid device protocol.")
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 40:
            raise DeviceInvalidInput("Invalid device protocol.")
        return normalized

    @staticmethod
    def _normalize_metadata(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise DeviceInvalidInput("Invalid device metadata.")
        normalized = value.strip() or None
        if normalized is not None and len(normalized) > 120:
            raise DeviceInvalidInput("Device metadata is too long.")
        return normalized

    async def create_device(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_type_id: UUID,
        device_uid: str,
        name: str,
        manufacturer: str | None = None,
        model: str | None = None,
        protocol: str = "mqtt",
    ) -> Device:
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_CREATE,
        )
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_CREATE,
        )

        if await self.repository.get_workspace(
            session, workspace_id=workspace_id
        ) is None:
            raise DeviceNotFound

        if await self.repository.get_device_type(
            session, device_type_id=device_type_id
        ) is None:
            raise DeviceTypeNotFound

        if not isinstance(device_uid, str) or not isinstance(name, str):
            raise DeviceInvalidInput("Invalid device identity.")
        clean_uid = device_uid.strip()
        clean_name = name.strip()
        if not clean_uid or len(clean_uid) > 160:
            raise DeviceInvalidInput("Invalid device UID.")
        if not clean_name or len(clean_name) > 160:
            raise DeviceInvalidInput("Invalid device name.")

        clean_manufacturer = self._normalize_metadata(manufacturer)
        clean_model = self._normalize_metadata(model)

        device = Device(
            workspace_id=workspace_id,
            device_type_id=device_type_id,
            device_uid=clean_uid,
            name=clean_name,
            manufacturer=clean_manufacturer,
            model=clean_model,
            protocol=self._normalize_protocol(protocol),
            lifecycle_status="pending_provisioning",
            is_enabled=True,
        )
        await self.repository.add_device(session, device=device)
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.created",
            resource_type="device",
            resource_id=device.id,
            details={
                "device_uid": device.device_uid,
                "device_type_id": str(device.device_type_id),
                "protocol": device.protocol,
                "lifecycle_status": device.lifecycle_status,
            },
        )
        return device

    async def list_devices(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Device]:
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_READ,
        )
        return await self.repository.list_devices(
            session,
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )

    async def get_device(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
    ) -> Device:
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_READ,
        )
        device = await self.repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
        )
        if device is None:
            raise DeviceNotFound
        return device

    async def update_device(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
        changes: dict,
    ) -> Device:
        allowed = {"name", "manufacturer", "model", "protocol"}
        if not changes or not set(changes).issubset(allowed):
            raise DeviceInvalidInput("Invalid device update fields.")

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        device = await self.repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            for_update=True,
        )
        if device is None:
            raise DeviceNotFound

        for field, value in changes.items():
            if field == "name":
                value = value.strip() if isinstance(value, str) else ""
                if not value or len(value) > 160:
                    raise DeviceInvalidInput("Invalid device name.")
            elif field == "protocol":
                value = self._normalize_protocol(value)
            elif field in {"manufacturer", "model"}:
                value = self._normalize_metadata(value)
            setattr(device, field, value)

        await session.flush()
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.updated",
            resource_type="device",
            resource_id=device.id,
            details={"changed_fields": sorted(changes)},
        )
        return device

    async def change_lifecycle(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
        new_status: str,
    ) -> Device:
        if not isinstance(new_status, str) or new_status not in LIFECYCLE_VALUES:
            raise DeviceInvalidInput("Unsupported device lifecycle status.")

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        await self.repository.lock_workspace(
            session, workspace_id=workspace_id
        )
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )
        device = await self.repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            for_update=True,
        )
        if device is None:
            raise DeviceNotFound

        current = device.lifecycle_status
        if current is None:
            raise DeviceStateConflict(
                "Legacy device lifecycle has not been initialized."
            )
        if current not in LIFECYCLE_TRANSITIONS:
            raise DeviceStateConflict("Device has an unsupported lifecycle status.")
        if new_status not in LIFECYCLE_TRANSITIONS[current]:
            raise DeviceStateConflict("Invalid lifecycle transition.")

        device.lifecycle_status = new_status
        if new_status == "active":
            device.is_enabled = True
        elif new_status in {"disabled", "revoked", "retired"}:
            device.is_enabled = False

        await session.flush()
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.lifecycle_changed",
            resource_type="device",
            resource_id=device.id,
            details={
                "previous_status": current,
                "new_status": new_status,
            },
        )
        return device
