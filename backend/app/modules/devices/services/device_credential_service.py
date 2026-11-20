"""Application service for secure device credential lifecycle management."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.devices.models import Device, DeviceCredential
from app.modules.devices.services.audit_repository import DeviceAuditRepository
from app.modules.devices.services.device_credential_repository import (
    DeviceCredentialRepository,
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
class DeviceCredentialMetadata:
    """Credential metadata without any secret material."""

    id: UUID
    broker_key: str
    credential_identifier: str
    credential_type: str
    credential_status: str
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    rotated_at: datetime | None
    last_used_at: datetime | None


@dataclass(frozen=True)
class ProvisionedDeviceCredential:
    """Credential provisioned with a one-time plaintext password."""

    metadata: DeviceCredentialMetadata
    password: str


class DeviceCredentialService:
    """Manage device credentials without persisting plaintext passwords."""

    def __init__(self) -> None:
        self.repository = DeviceCredentialRepository()
        self.device_repository = DeviceRepository()
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
    def _metadata(
        credential: DeviceCredential,
    ) -> DeviceCredentialMetadata:
        return DeviceCredentialMetadata(
            id=credential.id,
            broker_key=credential.broker_key,
            credential_identifier=credential.credential_identifier,
            credential_type=credential.credential_type,
            credential_status=credential.credential_status,
            created_at=credential.created_at,
            expires_at=credential.expires_at,
            revoked_at=credential.revoked_at,
            rotated_at=credential.rotated_at,
            last_used_at=credential.last_used_at,
        )

    @staticmethod
    def _validate_text(
        value: str,
        *,
        field: str,
        max_length: int,
    ) -> str:
        if not isinstance(value, str):
            raise DeviceInvalidInput(f"Invalid credential {field}.")

        normalized = value.strip()
        if not normalized or len(normalized) > max_length:
            raise DeviceInvalidInput(f"Invalid credential {field}.")

        return normalized

    async def _lock_active_device(
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
            or device.lifecycle_status != "active"
        ):
            raise DeviceStateConflict(
                "Device must be enabled and active."
            )

        return device

    async def _lock_credential_creation_device(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
    ) -> Device:
        """Lock a device eligible for initial provisioning or credential rotation."""

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
            or device.lifecycle_status not in {
                "pending_provisioning",
                "active",
            }
        ):
            raise DeviceStateConflict(
                "Device must be enabled and pending provisioning or active."
            )

        return device

    async def create_credential(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
        broker_key: str,
        credential_type: str = "mqtt_password",
        expires_at: datetime | None = None,
    ) -> ProvisionedDeviceCredential:
        """Create a pending credential and return its password exactly once."""

        broker_key = self._validate_text(
            broker_key,
            field="broker key",
            max_length=80,
        )
        credential_type = self._validate_text(
            credential_type,
            field="type",
            max_length=40,
        )

        if expires_at is not None:
            if (
                expires_at.tzinfo is None
                or expires_at.utcoffset() is None
                or expires_at <= datetime.now(timezone.utc)
            ):
                raise DeviceInvalidInput(
                    "Credential expiration must be a future timezone-aware datetime."
                )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )

        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )

        await self._lock_credential_creation_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
        )

        credential_identifier = (
            "dc_" + secrets.token_urlsafe(18)
        )
        password = secrets.token_urlsafe(32)
        secret_hash = hash_password(password)

        credential = await self.repository.create(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            broker_key=broker_key,
            credential_identifier=credential_identifier,
            credential_type=credential_type,
            secret_hash=secret_hash,
            expires_at=expires_at,
        )

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device_credential.created",
            resource_type="device_credential",
            resource_id=credential.id,
            details={
                "broker_key": broker_key,
                "credential_identifier": credential_identifier,
                "credential_type": credential_type,
                "credential_status": "pending",
            },
        )

        return ProvisionedDeviceCredential(
            metadata=self._metadata(credential),
            password=password,
        )

    async def list_credentials(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        device_id: UUID,
    ) -> list[DeviceCredentialMetadata]:
        """List safe credential metadata for a workspace device."""

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_READ,
        )

        device = await self.device_repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
        )

        if device is None:
            raise DeviceNotFound

        credentials = await self.repository.list_for_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
        )

        return [
            self._metadata(credential)
            for credential in credentials
        ]

    async def activate_credential(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        credential_id: UUID,
    ) -> DeviceCredentialMetadata:
        """Activate a pending credential belonging to an active device."""

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )

        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )

        credential = await self.repository.get(
            session,
            workspace_id=workspace_id,
            credential_id=credential_id,
            for_update=True,
        )

        if credential is None:
            raise DeviceNotFound

        await self._lock_active_device(
            session,
            workspace_id=workspace_id,
            device_id=credential.device_id,
        )

        if credential.credential_status != "pending":
            raise DeviceStateConflict(
                "Only pending credentials can be activated."
            )

        if (
            credential.expires_at is not None
            and credential.expires_at <= datetime.now(timezone.utc)
        ):
            raise DeviceStateConflict(
                "Expired credentials cannot be activated."
            )

        try:
            await self.repository.activate(
                session,
                credential=credential,
            )
        except ValueError:
            raise DeviceStateConflict(
                "Only pending credentials can be activated."
            ) from None

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device_credential.activated",
            resource_type="device_credential",
            resource_id=credential.id,
            details={
                "broker_key": credential.broker_key,
                "credential_identifier": credential.credential_identifier,
            },
        )

        return self._metadata(credential)

    async def revoke_credential(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        credential_id: UUID,
    ) -> DeviceCredentialMetadata:
        """Permanently revoke a pending or active credential."""

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )

        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.DEVICES_UPDATE,
        )

        credential = await self.repository.get(
            session,
            workspace_id=workspace_id,
            credential_id=credential_id,
            for_update=True,
        )

        if credential is None:
            raise DeviceNotFound

        if credential.credential_status == "revoked":
            raise DeviceStateConflict(
                "Credential has already been revoked."
            )

        revoked_at = datetime.now(timezone.utc)

        await self.repository.revoke(
            session,
            credential=credential,
            revoked_at=revoked_at,
        )

        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="device_credential.revoked",
            resource_type="device_credential",
            resource_id=credential.id,
            details={
                "broker_key": credential.broker_key,
                "credential_identifier": credential.credential_identifier,
            },
        )

        return self._metadata(credential)
