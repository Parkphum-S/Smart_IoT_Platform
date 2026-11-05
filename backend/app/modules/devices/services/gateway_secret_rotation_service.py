"""Internal batch key rotation for encrypted gateway secrets.

This service is intended for trusted maintenance jobs only.
Do not expose it through a public API.
The caller owns transaction commit and rollback.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.devices.services.device_repository import DeviceRepository
from app.modules.devices.services.gateway_secret_repository import (
    DeviceGatewaySecretRepository,
)
from app.modules.devices.services.gateway_secret_service import (
    build_gateway_secret_keyring,
)


@dataclass(frozen=True)
class GatewaySecretRotationBatch:
    """Result of one transaction-scoped rotation batch."""

    rotated_count: int


class GatewaySecretRotationService:
    """Rotate workspace gateway secrets to the configured active key."""

    MAX_BATCH_SIZE = 1000

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.repository = DeviceGatewaySecretRepository()
        self.device_repository = DeviceRepository()

    async def rotate_workspace_batch(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        batch_size: int = 100,
    ) -> GatewaySecretRotationBatch:
        """Rotate one bounded batch; transaction ownership stays with caller."""
        if type(batch_size) is not int or not 1 <= batch_size <= self.MAX_BATCH_SIZE:
            raise ValueError(
                f"batch_size must be between 1 and {self.MAX_BATCH_SIZE}."
            )

        keyring = build_gateway_secret_keyring(self.settings)

        # Coordinate with normal workspace-scoped device and secret mutations.
        await self.device_repository.lock_workspace(
            session,
            workspace_id=workspace_id,
        )

        secrets = await self.repository.list_for_rotation(
            session,
            workspace_id=workspace_id,
            active_key_version=keyring.key_version,
            limit=batch_size,
        )

        # Prepare every replacement before mutating ORM records. If any
        # ciphertext fails authentication, the batch remains unchanged.
        replacements = []

        for secret in secrets:
            plaintext = keyring.decrypt(
                secret.ciphertext,
                secret.key_version,
                workspace_id=str(secret.workspace_id),
                gateway_id=str(secret.gateway_device_id),
            )
            ciphertext = keyring.encrypt(
                plaintext,
                workspace_id=str(secret.workspace_id),
                gateway_id=str(secret.gateway_device_id),
            )
            replacements.append((secret, ciphertext))

        for secret, ciphertext in replacements:
            secret.ciphertext = ciphertext
            secret.key_version = keyring.key_version

        if replacements:
            # Flush only. Never commit or rollback inside this service.
            await session.flush()

        return GatewaySecretRotationBatch(rotated_count=len(secrets))
