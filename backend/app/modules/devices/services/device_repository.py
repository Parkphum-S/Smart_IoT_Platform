"""Persistence operations for devices."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import Device, DeviceType
from app.modules.users.models import Workspace


class DeviceRepository:
    """Database operations; transaction ownership remains with the caller."""

    async def lock_workspace(
        self, session: AsyncSession, *, workspace_id: UUID
    ) -> None:
        await session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtextextended(str(workspace_id), 0)
                )
            )
        )

    async def get_workspace(
        self, session: AsyncSession, *, workspace_id: UUID
    ) -> Workspace | None:
        result = await session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_device_type(
        self, session: AsyncSession, *, device_type_id: UUID
    ) -> DeviceType | None:
        result = await session.execute(
            select(DeviceType).where(DeviceType.id == device_type_id)
        )
        return result.scalar_one_or_none()

    async def get_device(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
        for_update: bool = False,
    ) -> Device | None:
        statement = select(Device).where(
            Device.workspace_id == workspace_id,
            Device.id == device_id,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def list_devices(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Device]:
        statement = (
            select(Device)
            .where(Device.workspace_id == workspace_id)
            .order_by(Device.name, Device.id)
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def add_device(
        self, session: AsyncSession, *, device: Device
    ) -> Device:
        session.add(device)
        await session.flush()
        return device
