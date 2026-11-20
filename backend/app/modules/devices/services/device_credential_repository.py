"""Persistence operations for broker-scoped device credentials."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import Device, DeviceCredential


class DeviceCredentialRepository:
    """Workspace-scoped credential persistence.

    Transaction ownership remains with the caller.
    This repository never commits or rolls back.
    """

    async def get(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        credential_id: UUID,
        for_update: bool = False,
    ) -> DeviceCredential | None:
        statement = select(DeviceCredential).where(
            DeviceCredential.workspace_id == workspace_id,
            DeviceCredential.id == credential_id,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_identifier(
        self,
        session: AsyncSession,
        *,
        broker_key: str,
        credential_identifier: str,
        for_update: bool = False,
    ) -> DeviceCredential | None:
        """Find a credential using its broker-scoped identifier."""
        statement = select(DeviceCredential).where(
            DeviceCredential.broker_key == broker_key,
            DeviceCredential.credential_identifier == credential_identifier,
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
        device_id: UUID,
        broker_key: str,
        credential_identifier: str,
        for_update: bool = False,
    ) -> DeviceCredential | None:
        """Find a credential bound to the enrolling workspace device."""
        statement = select(DeviceCredential).where(
            DeviceCredential.workspace_id == workspace_id,
            DeviceCredential.device_id == device_id,
            DeviceCredential.broker_key == broker_key,
            DeviceCredential.credential_identifier
            == credential_identifier,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_for_authentication(
        self,
        session: AsyncSession,
        *,
        broker_key: str,
        credential_identifier: str,
    ) -> DeviceCredential | None:
        """Return an eligible credential for broker authentication.

        Password verification must still be performed by the trusted
        authentication layer. This method only checks credential and
        associated device eligibility.
        """
        statement = (
            select(DeviceCredential)
            .join(
                Device,
                (
                    Device.id == DeviceCredential.device_id
                )
                & (
                    Device.workspace_id
                    == DeviceCredential.workspace_id
                ),
            )
            .where(
                DeviceCredential.broker_key == broker_key,
                DeviceCredential.credential_identifier
                == credential_identifier,
                DeviceCredential.credential_status == "active",
                DeviceCredential.secret_hash.is_not(None),
                or_(
                    DeviceCredential.expires_at.is_(None),
                    DeviceCredential.expires_at > func.now(),
                ),
                Device.is_enabled.is_(True),
                Device.lifecycle_status == "active",
            )
        )

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_device(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
    ) -> list[DeviceCredential]:
        """List credential records belonging to a workspace device."""
        statement = (
            select(DeviceCredential)
            .where(
                DeviceCredential.workspace_id == workspace_id,
                DeviceCredential.device_id == device_id,
            )
            .order_by(
                DeviceCredential.created_at.desc(),
                DeviceCredential.id,
            )
        )

        result = await session.execute(statement)
        return list(result.scalars().all())

    async def create(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
        broker_key: str,
        credential_identifier: str,
        credential_type: str,
        secret_hash: str | None = None,
        secret_reference: str | None = None,
        expires_at: datetime | None = None,
    ) -> DeviceCredential:
        """Create a pending credential and flush it."""
        credential = DeviceCredential(
            workspace_id=workspace_id,
            device_id=device_id,
            broker_key=broker_key,
            credential_identifier=credential_identifier,
            credential_type=credential_type,
            secret_hash=secret_hash,
            secret_reference=secret_reference,
            expires_at=expires_at,
            credential_status="pending",
        )

        session.add(credential)
        await session.flush()
        return credential

    async def activate(
        self,
        session: AsyncSession,
        *,
        credential: DeviceCredential,
    ) -> DeviceCredential:
        """Set a credential to active.

        Lifecycle validation belongs to the service layer.
        """
        if credential.credential_status != "pending":
            raise ValueError(
                "Only pending credentials can be activated."
            )

        credential.credential_status = "active"

        await session.flush()
        return credential

    async def revoke(
        self,
        session: AsyncSession,
        *,
        credential: DeviceCredential,
        revoked_at: datetime,
    ) -> DeviceCredential:
        """Revoke a credential at the supplied timestamp."""
        credential.credential_status = "revoked"
        credential.revoked_at = revoked_at

        await session.flush()
        return credential

    async def mark_rotated(
        self,
        session: AsyncSession,
        *,
        credential: DeviceCredential,
        rotated_at: datetime,
    ) -> DeviceCredential:
        """Record when an existing credential was superseded."""
        credential.rotated_at = rotated_at

        await session.flush()
        return credential

    async def update_last_used(
        self,
        session: AsyncSession,
        *,
        credential: DeviceCredential,
        last_used_at: datetime,
    ) -> DeviceCredential:
        """Update the last successful authentication timestamp."""
        credential.last_used_at = last_used_at

        await session.flush()
        return credential
