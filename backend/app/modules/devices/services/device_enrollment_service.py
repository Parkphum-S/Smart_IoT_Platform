"""Atomic device enrollment using a single-use bootstrap token."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.devices.models import Device, DeviceCredential
from app.modules.devices.services.audit_repository import DeviceAuditRepository
from app.modules.devices.services.device_bootstrap_token_repository import (
    DeviceBootstrapTokenRepository,
)
from app.modules.devices.services.device_credential_repository import (
    DeviceCredentialRepository,
)
from app.modules.devices.services.device_repository import DeviceRepository
from app.modules.devices.services.exceptions import DeviceEnrollmentFailed


@dataclass(frozen=True)
class DeviceEnrollmentResult:
    """Safe enrollment result without credential secrets."""

    device_id: UUID
    credential_id: UUID
    lifecycle_status: str
    credential_status: str


class DeviceEnrollmentService:
    """Authenticate and activate a device atomically.

    The caller owns the transaction. This service never commits or rolls
    back and never returns or logs bootstrap tokens or passwords.
    """

    def __init__(self) -> None:
        self.bootstrap_repository = DeviceBootstrapTokenRepository()
        self.credential_repository = DeviceCredentialRepository()
        self.device_repository = DeviceRepository()
        self.audit = DeviceAuditRepository()

    @staticmethod
    def _fail() -> None:
        """Raise one generic failure without exposing the failed condition."""
        raise DeviceEnrollmentFailed("Device enrollment failed.")

    @staticmethod
    def _validate_input(
        *,
        bootstrap_token: str,
        broker_key: str,
        credential_identifier: str,
        password: str,
    ) -> None:
        if (
            not isinstance(bootstrap_token, str)
            or not bootstrap_token
            or len(bootstrap_token) > 512
            or not isinstance(broker_key, str)
            or not broker_key
            or len(broker_key) > 80
            or not isinstance(credential_identifier, str)
            or not credential_identifier
            or len(credential_identifier) > 160
            or not isinstance(password, str)
            or not password
            or len(password) > 1024
        ):
            DeviceEnrollmentService._fail()

    async def enroll_device(
        self,
        session: AsyncSession,
        *,
        bootstrap_token: str,
        broker_key: str,
        credential_identifier: str,
        password: str,
    ) -> DeviceEnrollmentResult:
        """Validate proof of possession and activate device credentials."""

        self._validate_input(
            bootstrap_token=bootstrap_token,
            broker_key=broker_key,
            credential_identifier=credential_identifier,
            password=password,
        )

        token_hash = hashlib.sha256(
            bootstrap_token.encode("utf-8")
        ).hexdigest()

        # Initial lookup discovers the workspace and device.
        # It deliberately does not acquire a row lock.
        initial_token = await self.bootstrap_repository.get_for_validation(
            session,
            token_hash=token_hash,
        )
        if initial_token is None:
            self._fail()

        workspace_id = initial_token.workspace_id
        device_id = initial_token.device_id
        token_id = initial_token.id

        # Canonical lock order:
        # Workspace -> Device -> Bootstrap Token -> Credential.
        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        device = await self.device_repository.get_device(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            for_update=True,
        )
        if device is None:
            self._fail()

        token = await self.bootstrap_repository.get_for_enrollment(
            session,
            workspace_id=workspace_id,
            token_id=token_id,
            for_update=True,
        )

        now = datetime.now(timezone.utc)

        if (
            token is None
            or token.device_id != device.id
            or token.workspace_id != device.workspace_id
            or not secrets.compare_digest(token.token_hash, token_hash)
            or token.expires_at <= now
            or token.consumed_at is not None
            or token.revoked_at is not None
            or not device.is_enabled
            or device.lifecycle_status != "pending_provisioning"
        ):
            self._fail()

        credential = await self.credential_repository.get_for_enrollment(
            session,
            workspace_id=workspace_id,
            device_id=device_id,
            broker_key=broker_key,
            credential_identifier=credential_identifier,
            for_update=True,
        )

        if (
            credential is None
            or credential.workspace_id != workspace_id
            or credential.device_id != device.id
            or credential.broker_key != broker_key
            or credential.credential_identifier != credential_identifier
            or credential.credential_status != "pending"
            or credential.credential_type != "mqtt_password"
            or not credential.secret_hash
            or credential.secret_reference is not None
            or (
                credential.expires_at is not None
                and credential.expires_at <= now
            )
            or not verify_password(password, credential.secret_hash)
        ):
            self._fail()

        # All validations have passed. Every mutation below belongs
        # to the same caller-owned database transaction.
        try:
            await self.bootstrap_repository.consume(
                session,
                token=token,
                consumed_at=now,
            )
            await self.credential_repository.activate(
                session,
                credential=credential,
            )
            await self.device_repository.activate_after_enrollment(
                session,
                device=device,
            )
        except ValueError:
            self._fail()

        # Device is the actor that completed enrollment.
        # No token, password, hash, or credential identifier is recorded.
        await self.audit.record(
            session,
            workspace_id=workspace_id,
            actor_id=device.id,
            actor_type="device",
            action="device.enrolled",
            resource_type="device",
            resource_id=device.id,
            details={
                "credential_id": str(credential.id),
                "broker_key": credential.broker_key,
            },
        )

        return DeviceEnrollmentResult(
            device_id=device.id,
            credential_id=credential.id,
            lifecycle_status=device.lifecycle_status,
            credential_status=credential.credential_status,
        )
