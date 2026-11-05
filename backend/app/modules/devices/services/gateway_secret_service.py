"""Application service for encrypted gateway secret management."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.security.encryption import GatewaySecretKeyring
from app.modules.devices.models import DeviceGateway
from app.modules.devices.services.audit_repository import DeviceAuditRepository
from app.modules.devices.services.device_repository import DeviceRepository
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DevicePermissionDenied,
    GatewayNotFound,
    GatewaySecretAlreadyExists,
    GatewaySecretEncryptionUnavailable,
    GatewaySecretNotFound,
)
from app.modules.devices.services.gateway_secret_repository import (
    DeviceGatewaySecretRepository,
)
from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import Permission


_SECRET_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}")
_MAX_SECRET_VALUE_LENGTH = 16384


@dataclass(frozen=True)
class GatewaySecretMetadata:
    """Safe secret metadata that never contains encrypted or plaintext values."""

    secret_name: str
    created_at: datetime
    updated_at: datetime


def build_gateway_secret_keyring(settings: Settings) -> GatewaySecretKeyring:
    """Build the configured keyring with backward-compatible single-key support."""
    configured_keys = settings.gateway_encryption_keys

    if configured_keys:
        encoded_keys = {
            version: value.get_secret_value()
            for version, value in configured_keys.items()
        }
    elif settings.gateway_encryption_key is not None:
        encoded_keys = {
            settings.gateway_encryption_key_version:
                settings.gateway_encryption_key.get_secret_value()
        }
    else:
        raise GatewaySecretEncryptionUnavailable

    try:
        return GatewaySecretKeyring.from_base64(
            encoded_keys,
            settings.gateway_encryption_key_version,
        )
    except (ValueError, TypeError):
        raise GatewaySecretEncryptionUnavailable from None


class GatewaySecretService:
    """Manage gateway secrets without exposing their stored values."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.repository = DeviceGatewaySecretRepository()
        self.device_repository = DeviceRepository()
        self.audit = DeviceAuditRepository()
        self.authorization = AuthorizationService()

    async def _authorize(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        permission: Permission = Permission.DEVICES_UPDATE,
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




    def _get_keyring(self) -> GatewaySecretKeyring:
        """Load the configured gateway secret keyring."""
        return build_gateway_secret_keyring(self.settings)

    @staticmethod
    def _validate_secret_name(secret_name: str) -> str:
        if (
            not isinstance(secret_name, str)
            or _SECRET_NAME_PATTERN.fullmatch(secret_name) is None
        ):
            raise DeviceInvalidInput("Invalid gateway secret name.")

        return secret_name

    @staticmethod
    def _validate_secret_value(secret_value: str) -> str:
        if (
            not isinstance(secret_value, str)
            or not secret_value
            or len(secret_value) > _MAX_SECRET_VALUE_LENGTH
        ):
            raise DeviceInvalidInput("Invalid gateway secret value.")

        return secret_value

    async def _lock_gateway(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        gateway_device_id: UUID,
        for_update: bool = True,
    ) -> DeviceGateway:
        statement = select(DeviceGateway).where(
            DeviceGateway.workspace_id == workspace_id,
            DeviceGateway.device_id == gateway_device_id,
        )
        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        gateway = result.scalar_one_or_none()

        if gateway is None:
            raise GatewayNotFound

        return gateway

    @staticmethod
    def _metadata(secret) -> GatewaySecretMetadata:
        return GatewaySecretMetadata(
            secret_name=secret.secret_name,
            created_at=secret.created_at,
            updated_at=secret.updated_at,
        )

    async def list_secrets(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        gateway_device_id: UUID,
    ) -> list[GatewaySecretMetadata]:
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_READ,
        )
        await self._lock_gateway(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
            for_update=False,
        )

        secrets = await self.repository.list(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
        )
        return [self._metadata(secret) for secret in secrets]

    async def create_secret(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        gateway_device_id: UUID,
        secret_name: str,
        secret_value: str,
    ) -> GatewaySecretMetadata:
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
        await self._lock_gateway(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
        )

        secret_name = self._validate_secret_name(secret_name)
        secret_value = self._validate_secret_value(secret_value)

        existing = await self.repository.get(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
            secret_name=secret_name,
        )
        if existing is not None:
            raise GatewaySecretAlreadyExists

        encryption = self._get_keyring()
        ciphertext = encryption.encrypt(
            secret_value,
            workspace_id=str(workspace_id),
            gateway_id=str(gateway_device_id),
        )

        secret = await self.repository.create(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
            secret_name=secret_name,
            ciphertext=ciphertext,
            key_version=encryption.key_version,
        )

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway_secret.created",
            resource_type="device_gateway_secret",
            resource_id=gateway_device_id,
            details={"secret_name": secret_name},
        )

        return self._metadata(secret)

    async def update_secret(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        gateway_device_id: UUID,
        secret_name: str,
        secret_value: str,
    ) -> GatewaySecretMetadata:
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
        await self._lock_gateway(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
        )

        secret_name = self._validate_secret_name(secret_name)
        secret_value = self._validate_secret_value(secret_value)

        secret = await self.repository.get(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
            secret_name=secret_name,
            for_update=True,
        )
        if secret is None:
            raise GatewaySecretNotFound

        encryption = self._get_keyring()
        ciphertext = encryption.encrypt(
            secret_value,
            workspace_id=str(workspace_id),
            gateway_id=str(gateway_device_id),
        )

        updated = await self.repository.update(
            session,
            secret=secret,
            ciphertext=ciphertext,
            key_version=encryption.key_version,
        )

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway_secret.updated",
            resource_type="device_gateway_secret",
            resource_id=gateway_device_id,
            details={"secret_name": secret_name},
        )

        return self._metadata(updated)

    async def delete_secret(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        gateway_device_id: UUID,
        secret_name: str,
    ) -> None:
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
        await self._lock_gateway(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
        )

        secret_name = self._validate_secret_name(secret_name)

        secret = await self.repository.get(
            session,
            workspace_id=workspace_id,
            gateway_device_id=gateway_device_id,
            secret_name=secret_name,
            for_update=True,
        )
        if secret is None:
            raise GatewaySecretNotFound

        await self.repository.delete(session, secret=secret)

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device.gateway_secret.deleted",
            resource_type="device_gateway_secret",
            resource_id=gateway_device_id,
            details={"secret_name": secret_name},
        )
