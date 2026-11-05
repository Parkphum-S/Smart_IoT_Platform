"""Persistence operations for encrypted gateway secrets."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import DeviceGatewaySecret


class DeviceGatewaySecretRepository:
    """Workspace-scoped persistence; transaction belongs to the caller."""

    async def get(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        gateway_device_id: UUID,
        secret_name: str,
        for_update: bool = False,
    ) -> DeviceGatewaySecret | None:
        statement = select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace_id,
            DeviceGatewaySecret.gateway_device_id == gateway_device_id,
            DeviceGatewaySecret.secret_name == secret_name,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        gateway_device_id: UUID,
    ) -> list[DeviceGatewaySecret]:
        statement = (
            select(DeviceGatewaySecret)
            .where(
                DeviceGatewaySecret.workspace_id == workspace_id,
                DeviceGatewaySecret.gateway_device_id == gateway_device_id,
            )
            .order_by(DeviceGatewaySecret.secret_name)
        )

        result = await session.execute(statement)
        return list(result.scalars().all())

    async def list_for_rotation(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        active_key_version: str,
        limit: int,
    ) -> list[DeviceGatewaySecret]:
        """Lock and return a bounded batch of secrets using older keys."""
        statement = (
            select(DeviceGatewaySecret)
            .where(
                DeviceGatewaySecret.workspace_id == workspace_id,
                DeviceGatewaySecret.key_version != active_key_version,
            )
            .order_by(
                DeviceGatewaySecret.gateway_device_id,
                DeviceGatewaySecret.secret_name,
            )
            .limit(limit)
            .with_for_update()
        )
        result = await session.execute(statement)
        return list(result.scalars().all())


    async def get_key_version_counts(
        self,
        session: AsyncSession,
    ) -> dict[str, int]:
        """Return global secret counts grouped by key version.

        Only version identifiers and counts are returned; ciphertext and
        plaintext are never selected.
        """
        statement = (
            select(
                DeviceGatewaySecret.key_version,
                func.count().label("secret_count"),
            )
            .group_by(DeviceGatewaySecret.key_version)
            .order_by(DeviceGatewaySecret.key_version)
        )
        result = await session.execute(statement)
        return {
            version: count
            for version, count in result.all()
        }

    async def create(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        gateway_device_id: UUID,
        secret_name: str,
        ciphertext: str,
        key_version: str,
    ) -> DeviceGatewaySecret:
        secret = DeviceGatewaySecret(
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
            secret_name=secret_name,
            ciphertext=ciphertext,
            key_version=key_version,
        )
        session.add(secret)
        await session.flush()
        return secret

    async def update(
        self,
        session: AsyncSession,
        *,
        secret: DeviceGatewaySecret,
        ciphertext: str,
        key_version: str,
    ) -> DeviceGatewaySecret:
        secret.ciphertext = ciphertext
        secret.key_version = key_version
        await session.flush()
        await session.refresh(secret, attribute_names=["updated_at"])
        return secret

    async def delete(
        self,
        session: AsyncSession,
        *,
        secret: DeviceGatewaySecret,
    ) -> None:
        await session.delete(secret)
        await session.flush()
