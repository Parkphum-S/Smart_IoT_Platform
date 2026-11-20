import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.devices.services import (
    device_bootstrap_token_service as service_module,
)
from app.modules.devices.services.device_bootstrap_token_service import (
    DeviceBootstrapTokenMetadata,
    DeviceBootstrapTokenService,
    ProvisionedDeviceBootstrapToken,
)
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    DeviceStateConflict,
)
from app.modules.users.services.authorization.authorization_service import (
    PermissionDenied,
)


@pytest.fixture
def identifiers():
    return {
        "actor_id": uuid4(),
        "workspace_id": uuid4(),
        "device_id": uuid4(),
        "token_id": uuid4(),
    }


@pytest.fixture
def service():
    instance = DeviceBootstrapTokenService()

    instance.repository = SimpleNamespace(
        create=AsyncMock(),
        get=AsyncMock(),
        revoke=AsyncMock(),
    )

    instance.device_repository = SimpleNamespace(
        lock_workspace=AsyncMock(),
        get_device=AsyncMock(),
    )

    instance.audit = SimpleNamespace(
        record=AsyncMock(),
    )

    instance.authorization = SimpleNamespace(
        authorize=AsyncMock(),
    )

    return instance


@pytest.fixture
def pending_device(identifiers):
    return SimpleNamespace(
        id=identifiers["device_id"],
        workspace_id=identifiers["workspace_id"],
        is_enabled=True,
        lifecycle_status="pending_provisioning",
    )


@pytest.fixture
def unused_token(identifiers):
    return SimpleNamespace(
        id=identifiers["token_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
        token_hash="a" * 64,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        consumed_at=None,
        revoked_at=None,
    )


@pytest.mark.asyncio
async def test_create_token_returns_plaintext_once_and_stores_hash(
    service, identifiers, pending_device, monkeypatch
):
    plaintext = "generated-bootstrap-token"

    monkeypatch.setattr(
        service_module.secrets,
        "token_urlsafe",
        lambda size: plaintext,
    )

    token_record = SimpleNamespace(
        id=identifiers["token_id"],
        device_id=identifiers["device_id"],
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        consumed_at=None,
        revoked_at=None,
    )

    service.device_repository.get_device.return_value = pending_device
    service.repository.create.return_value = token_record

    result = await service.create_token(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
    )

    assert isinstance(result, ProvisionedDeviceBootstrapToken)
    assert result.token == plaintext
    assert result.metadata.id == identifiers["token_id"]

    create_kwargs = service.repository.create.await_args.kwargs

    assert create_kwargs["workspace_id"] == identifiers["workspace_id"]
    assert create_kwargs["device_id"] == identifiers["device_id"]
    assert create_kwargs["token_hash"] == hashlib.sha256(
        plaintext.encode("utf-8")
    ).hexdigest()
    assert create_kwargs["token_hash"] != plaintext
    assert create_kwargs["expires_at"] > datetime.now(timezone.utc)

    audit_details = service.audit.record.await_args.kwargs["details"]

    assert "token" not in audit_details
    assert "token_hash" not in audit_details
    assert plaintext not in str(audit_details)

    assert service.authorization.authorize.await_count == 2
    service.device_repository.lock_workspace.assert_awaited_once()
    service.device_repository.get_device.assert_awaited_once()
    service.repository.create.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ttl_seconds",
    [True, False, 0, 59, 3601, -1, 1.5, "900", None],
)
async def test_create_token_rejects_invalid_ttl(
    service, identifiers, ttl_seconds
):
    with pytest.raises(DeviceInvalidInput):
        await service.create_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
            ttl_seconds=ttl_seconds,
        )

    service.authorization.authorize.assert_not_awaited()
    service.repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_token_rejects_device_not_found(
    service, identifiers
):
    service.device_repository.get_device.return_value = None

    with pytest.raises(DeviceNotFound):
        await service.create_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
        )

    service.repository.create.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device",
    [
        SimpleNamespace(
            is_enabled=False,
            lifecycle_status="pending_provisioning",
        ),
        SimpleNamespace(
            is_enabled=True,
            lifecycle_status="active",
        ),
    ],
)
async def test_create_token_rejects_ineligible_device(
    service, identifiers, device
):
    service.device_repository.get_device.return_value = device

    with pytest.raises(DeviceStateConflict):
        await service.create_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
        )

    service.repository.create.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_token_rejects_missing_permission(
    service, identifiers
):
    service.authorization.authorize.side_effect = PermissionDenied

    with pytest.raises(DevicePermissionDenied):
        await service.create_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
        )

    service.device_repository.lock_workspace.assert_not_awaited()
    service.repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_token_success(
    service, identifiers, unused_token
):
    service.repository.get.return_value = unused_token

    async def revoke(*args, **kwargs):
        kwargs["token"].revoked_at = kwargs["revoked_at"]

    service.repository.revoke.side_effect = revoke

    result = await service.revoke_token(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        token_id=identifiers["token_id"],
    )

    assert isinstance(result, DeviceBootstrapTokenMetadata)
    assert result.id == identifiers["token_id"]
    assert result.revoked_at is not None

    service.repository.get.assert_awaited_once_with(
        None,
        workspace_id=identifiers["workspace_id"],
        token_id=identifiers["token_id"],
        for_update=True,
    )

    service.repository.revoke.assert_awaited_once()
    service.audit.record.assert_awaited_once()

    audit_kwargs = service.audit.record.await_args.kwargs
    assert audit_kwargs["action"] == "device_bootstrap_token.revoked"
    assert "token_hash" not in audit_kwargs["details"]


@pytest.mark.asyncio
async def test_revoke_token_rejects_missing_token(
    service, identifiers
):
    service.repository.get.return_value = None

    with pytest.raises(DeviceNotFound):
        await service.revoke_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            token_id=identifiers["token_id"],
        )

    service.repository.revoke.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_token_rejects_consumed_token(
    service, identifiers, unused_token
):
    unused_token.consumed_at = datetime.now(timezone.utc)
    service.repository.get.return_value = unused_token

    with pytest.raises(DeviceStateConflict):
        await service.revoke_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            token_id=identifiers["token_id"],
        )

    service.repository.revoke.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_token_rejects_already_revoked_token(
    service, identifiers, unused_token
):
    unused_token.revoked_at = datetime.now(timezone.utc)
    service.repository.get.return_value = unused_token

    with pytest.raises(DeviceStateConflict):
        await service.revoke_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            token_id=identifiers["token_id"],
        )

    service.repository.revoke.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_token_handles_repository_race(
    service, identifiers, unused_token
):
    service.repository.get.return_value = unused_token
    service.repository.revoke.side_effect = ValueError(
        "Bootstrap token is no longer revocable."
    )

    with pytest.raises(DeviceStateConflict):
        await service.revoke_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            token_id=identifiers["token_id"],
        )

    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_token_rejects_missing_permission(
    service, identifiers
):
    service.authorization.authorize.side_effect = PermissionDenied

    with pytest.raises(DevicePermissionDenied):
        await service.revoke_token(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            token_id=identifiers["token_id"],
        )

    service.device_repository.lock_workspace.assert_not_awaited()
    service.repository.get.assert_not_awaited()
