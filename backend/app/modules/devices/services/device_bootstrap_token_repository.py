"""Persistence operations for single-use device bootstrap tokens."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import Device, DeviceBootstrapToken


class DeviceBootstrapTokenRepository:
    """Workspace-scoped bootstrap token persistence.

    Transaction ownership remains with the caller.
    This repository never commits or rolls back.
    """

    async def create(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> DeviceBootstrapToken:
        """Create a bootstrap token record using its hash only."""
        token = DeviceBootstrapToken(
            workspace_id=workspace_id,
            device_id=device_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        session.add(token)
        await session.flush()
        return token

    async def get(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        token_id: UUID,
        for_update: bool = False,
    ) -> DeviceBootstrapToken | None:
        """Find a bootstrap token within its workspace."""
        statement = select(DeviceBootstrapToken).where(
            DeviceBootstrapToken.workspace_id == workspace_id,
            DeviceBootstrapToken.id == token_id,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_for_enrollment(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        token_id: UUID,
        for_update: bool = False,
    ) -> DeviceBootstrapToken | None:
        """Lock and retrieve a token scoped to its enrolling workspace."""
        return await self.get(
            session,
            workspace_id=workspace_id,
            token_id=token_id,
            for_update=for_update,
        )

    async def get_by_hash(
        self,
        session: AsyncSession,
        *,
        token_hash: str,
        for_update: bool = False,
    ) -> DeviceBootstrapToken | None:
        """Find a token by its SHA-256 hash."""
        statement = select(DeviceBootstrapToken).where(
            DeviceBootstrapToken.token_hash == token_hash,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_for_validation(
        self,
        session: AsyncSession,
        *,
        token_hash: str,
        for_update: bool = False,
    ) -> DeviceBootstrapToken | None:
        """Find a valid token bound to an eligible pending device.

        The caller must subsequently lock the associated Device row
        using DeviceRepository.get_device(for_update=True), and
        revalidate its state in the same transaction.
        """
        statement = (
            select(DeviceBootstrapToken)
            .join(
                Device,
                (
                    Device.id == DeviceBootstrapToken.device_id
                )
                & (
                    Device.workspace_id
                    == DeviceBootstrapToken.workspace_id
                ),
            )
            .where(
                DeviceBootstrapToken.token_hash == token_hash,
                DeviceBootstrapToken.expires_at > func.now(),
                DeviceBootstrapToken.consumed_at.is_(None),
                DeviceBootstrapToken.revoked_at.is_(None),
                Device.is_enabled.is_(True),
                Device.lifecycle_status == "pending_provisioning",
            )
        )

        if for_update:
            statement = statement.with_for_update(
                of=DeviceBootstrapToken
            )

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def consume(
        self,
        session: AsyncSession,
        *,
        token: DeviceBootstrapToken,
        consumed_at: datetime,
    ) -> DeviceBootstrapToken:
        """Atomically consume an unexpired, unused bootstrap token.

        PostgreSQL evaluates expiration and terminal-state conditions
        as part of the UPDATE, preventing stale ORM state from
        authorizing token reuse.
        """
        statement = (
            update(DeviceBootstrapToken)
            .where(
                DeviceBootstrapToken.id == token.id,
                DeviceBootstrapToken.consumed_at.is_(None),
                DeviceBootstrapToken.revoked_at.is_(None),
                DeviceBootstrapToken.expires_at > func.now(),
            )
            .values(consumed_at=consumed_at)
            .returning(DeviceBootstrapToken.id)
            .execution_options(synchronize_session=False)
        )

        result = await session.execute(statement)
        consumed_id = result.scalar_one_or_none()

        if consumed_id is None:
            raise ValueError(
                "Bootstrap token is expired, consumed, or revoked."
            )

        token.consumed_at = consumed_at
        return token

    async def revoke(
        self,
        session: AsyncSession,
        *,
        token: DeviceBootstrapToken,
        revoked_at: datetime,
    ) -> DeviceBootstrapToken:
        """Atomically revoke an unused bootstrap token."""
        statement = (
            update(DeviceBootstrapToken)
            .where(
                DeviceBootstrapToken.id == token.id,
                DeviceBootstrapToken.consumed_at.is_(None),
                DeviceBootstrapToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
            .returning(DeviceBootstrapToken.id)
            .execution_options(synchronize_session=False)
        )

        result = await session.execute(statement)
        revoked_id = result.scalar_one_or_none()

        if revoked_id is None:
            raise ValueError(
                "Bootstrap token is already consumed or revoked."
            )

        token.revoked_at = revoked_at
        return token
