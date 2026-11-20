"""Application service for secure device bootstrap token lifecycle."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.devices.models import Device, DeviceBootstrapToken
from app.modules.devices.services.audit_repository import DeviceAuditRepository
from app.modules.devices.services.device_bootstrap_token_repository import (
    DeviceBootstrapTokenRepository,
)
from app.modules.devices.services.device_repository import DeviceRepository
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    DeviceStateConflict,
)
from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import Permission


@dataclass(frozen=True)
class DeviceBootstrapTokenMetadata:
    """Bootstrap token metadata without secret material."""

    id: UUID
    device_id: UUID
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class ProvisionedDeviceBootstrapToken:
    """Bootstrap token returned exactly once."""

    metadata: DeviceBootstrapTokenMetadata
    token: str


class DeviceBootstrapTokenService:
    """Manage device-bound, single-use bootstrap tokens."""

    DEFAULT_TTL_SECONDS = 900
    MIN_TTL_SECONDS = 60
    MAX_TTL_SECONDS = 3600

    def __init__(self) -> None:
        self.repository = DeviceBootstrapTokenRepository()
        self.device_repository = DeviceRepository()
        self.audit = DeviceAuditRepository()
        self.authorization = AuthorizationService()

    async def _authorize(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
    ) -> None:
        try:
            await self.authorization.authorize(
                session,
                user_id=actor_id,
                workspace_id=workspace_id,
                permission=Permission.DEVICES_UPDATE.value,
            )
        except (WorkspaceMembershipNotFound, PermissionDenied):
            raise DevicePermissionDenied from None

    @staticmethod
    def _metadata(
        token: DeviceBootstrapToken,
    ) -> DeviceBootstrapTokenMetadata:
        return DeviceBootstrapTokenMetadata(
            id=token.id,
            device_id=token.device_id,
            created_at=token.created_at,
            expires_at=token.expires_at,
            consumed_at=token.consumed_at,
            revoked_at=token.revoked_at,
        )

    async def _lock_eligible_device(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
    ) -> Device:
        device = await self.device_repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            for_update=True,
        )

        if device is None:
            raise DeviceNotFound

        if (
            not device.is_enabled
            or device.lifecycle_status != "pending_provisioning"
        ):
            raise DeviceStateConflict(
                "Bootstrap tokens require an enabled device "
                "in pending_provisioning state."
            )

        return device

    async def create_token(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> ProvisionedDeviceBootstrapToken:
        """Create a hashed bootstrap token and return plaintext once."""

        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or not self.MIN_TTL_SECONDS
            <= ttl_seconds
            <= self.MAX_TTL_SECONDS
        ):
            raise DeviceInvalidInput(
                "Bootstrap token TTL must be between 60 and 3600 seconds."
            )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
        )

        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
        )

        await self._lock_eligible_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
        )

        plaintext_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(
            plaintext_token.encode("utf-8")
        ).hexdigest()

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        token = await self.repository.create(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device_bootstrap_token.created",
            resource_type="device_bootstrap_token",
            resource_id=token.id,
            details={
                "device_id": str(device_id),
                "expires_at": expires_at.isoformat(),
            },
        )

        return ProvisionedDeviceBootstrapToken(
            metadata=self._metadata(token),
            token=plaintext_token,
        )

    async def revoke_token(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        token_id: UUID,
    ) -> DeviceBootstrapTokenMetadata:
        """Revoke an unused bootstrap token within its workspace."""

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
        )

        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
        )

        token = await self.repository.get(
            session,
            workspace_id=workspace_id,
            token_id=token_id,
            for_update=True,
        )

        if token is None:
            raise DeviceNotFound

        if token.consumed_at is not None:
            raise DeviceStateConflict(
                "Consumed bootstrap tokens cannot be revoked."
            )

        if token.revoked_at is not None:
            raise DeviceStateConflict(
                "Bootstrap token has already been revoked."
            )

        revoked_at = datetime.now(timezone.utc)

        try:
            await self.repository.revoke(
                session,
                token=token,
                revoked_at=revoked_at,
            )
        except ValueError:
            raise DeviceStateConflict(
                "Bootstrap token is no longer revocable."
            ) from None

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device_bootstrap_token.revoked",
            resource_type="device_bootstrap_token",
            resource_id=token.id,
            details={
                "device_id": str(token.device_id),
            },
        )

        return self._metadata(token)
