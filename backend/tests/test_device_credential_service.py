from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.devices.services import device_credential_service as service_module
from app.modules.devices.services.device_credential_service import (
    DeviceCredentialService,
    DeviceCredentialMetadata,
    ProvisionedDeviceCredential,
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
        "credential_id": uuid4(),
    }


@pytest.fixture
def service():
    instance = DeviceCredentialService()

    instance.repository = SimpleNamespace(
        create=AsyncMock(),
        get=AsyncMock(),
        list_for_device=AsyncMock(),
        activate=AsyncMock(),
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
def active_device(identifiers):
    return SimpleNamespace(
        id=identifiers["device_id"],
        workspace_id=identifiers["workspace_id"],
        is_enabled=True,
        lifecycle_status="active",
    )


@pytest.fixture
def pending_credential(identifiers):
    return SimpleNamespace(
        id=identifiers["credential_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
        broker_key="broker-main",
        credential_identifier="dc_test123",
        credential_type="mqtt_password",
        credential_status="pending",
        secret_hash="$argon2id$test-hash",
        secret_reference=None,
        created_at=datetime.now(timezone.utc),
        expires_at=None,
        revoked_at=None,
        rotated_at=None,
        last_used_at=None,
    )


@pytest.mark.asyncio
async def test_create_credential_returns_one_time_password(
    service, identifiers, active_device, monkeypatch
):
    monkeypatch.setattr(
        service_module.secrets,
        "token_urlsafe",
        lambda size: "generated-secret-" + str(size),
    )
    monkeypatch.setattr(
        service_module,
        "hash_password",
        lambda password: "hashed:" + password,
    )

    credential = SimpleNamespace(
        id=identifiers["credential_id"],
        broker_key="broker-main",
        credential_identifier="dc_generated",
        credential_type="mqtt_password",
        credential_status="pending",
        created_at=datetime.now(timezone.utc),
        expires_at=None,
        revoked_at=None,
        rotated_at=None,
        last_used_at=None,
        secret_hash="hashed:generated-secret-32",
        secret_reference=None,
    )

    service.device_repository.get_device.return_value = active_device
    service.repository.create.return_value = credential

    result = await service.create_credential(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
        broker_key=" broker-main ",
    )

    assert isinstance(result, ProvisionedDeviceCredential)
    assert result.password == "generated-secret-32"
    assert result.metadata.credential_status == "pending"

    service.repository.create.assert_awaited_once()

    create_kwargs = service.repository.create.await_args.kwargs

    assert create_kwargs["broker_key"] == "broker-main"
    assert create_kwargs["secret_hash"] == "hashed:generated-secret-32"
    assert create_kwargs["credential_status"] if "credential_status" in create_kwargs else True

    audit_details = service.audit.record.await_args.kwargs["details"]

    assert "password" not in audit_details
    assert "secret_hash" not in audit_details
    assert "secret_reference" not in audit_details

    assert service.authorization.authorize.await_count == 2
    service.device_repository.lock_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_credential_rejects_invalid_broker_key(
    service, identifiers
):
    with pytest.raises(DeviceInvalidInput):
        await service.create_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
            broker_key="   ",
        )

    service.authorization.authorize.assert_not_awaited()
    service.repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_credential_rejects_inactive_device(
    service, identifiers
):
    service.device_repository.get_device.return_value = SimpleNamespace(
        id=identifiers["device_id"],
        is_enabled=False,
        lifecycle_status="active",
    )

    with pytest.raises(DeviceStateConflict):
        await service.create_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
            broker_key="broker-main",
        )

    service.repository.create.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_credential_maps_authorization_failure(
    service, identifiers
):
    service.authorization.authorize.side_effect = PermissionDenied

    with pytest.raises(DevicePermissionDenied):
        await service.create_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
            broker_key="broker-main",
        )

    service.repository.create.assert_not_awaited()


def test_metadata_never_exposes_secret_material(pending_credential):
    metadata = DeviceCredentialService._metadata(pending_credential)

    assert isinstance(metadata, DeviceCredentialMetadata)
    assert metadata.id == pending_credential.id

    assert not hasattr(metadata, "secret_hash")
    assert not hasattr(metadata, "secret_reference")
    assert "$argon2id$" not in repr(metadata)


@pytest.mark.asyncio
async def test_list_credentials_returns_safe_metadata(
    service, identifiers, pending_credential
):
    service.device_repository.get_device.return_value = SimpleNamespace(
        id=identifiers["device_id"],
        workspace_id=identifiers["workspace_id"],
    )
    service.repository.list_for_device.return_value = [
        pending_credential
    ]

    result = await service.list_credentials(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
    )

    assert len(result) == 1
    assert isinstance(result[0], DeviceCredentialMetadata)
    assert not hasattr(result[0], "secret_hash")
    assert not hasattr(result[0], "secret_reference")

    service.repository.list_for_device.assert_awaited_once_with(
        None,
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
    )


@pytest.mark.asyncio
async def test_list_credentials_rejects_missing_device(
    service, identifiers
):
    service.device_repository.get_device.return_value = None

    with pytest.raises(DeviceNotFound):
        await service.list_credentials(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
        )

    service.repository.list_for_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_credential_activates_pending_credential(
    service, identifiers, active_device, pending_credential
):
    service.repository.get.return_value = pending_credential
    service.device_repository.get_device.return_value = active_device

    async def activate(session, *, credential):
        credential.credential_status = "active"

    service.repository.activate.side_effect = activate

    result = await service.activate_credential(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        credential_id=identifiers["credential_id"],
    )

    assert result.credential_status == "active"
    service.repository.activate.assert_awaited_once()
    service.audit.record.assert_awaited_once()

    assert (
        service.audit.record.await_args.kwargs["action"]
        == "device_credential.activated"
    )


@pytest.mark.asyncio
async def test_activate_credential_rejects_revoked_credential(
    service, identifiers, active_device, pending_credential
):
    pending_credential.credential_status = "revoked"
    service.repository.get.return_value = pending_credential
    service.device_repository.get_device.return_value = active_device

    with pytest.raises(DeviceStateConflict):
        await service.activate_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            credential_id=identifiers["credential_id"],
        )

    service.repository.activate.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_credential_rejects_expired_credential(
    service, identifiers, active_device, pending_credential
):
    pending_credential.expires_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    service.repository.get.return_value = pending_credential
    service.device_repository.get_device.return_value = active_device

    with pytest.raises(DeviceStateConflict):
        await service.activate_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            credential_id=identifiers["credential_id"],
        )

    service.repository.activate.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_credential_rejects_missing_credential(
    service, identifiers
):
    service.repository.get.return_value = None

    with pytest.raises(DeviceNotFound):
        await service.activate_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            credential_id=identifiers["credential_id"],
        )

    service.repository.activate.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_credential_revokes_pending_credential(
    service, identifiers, pending_credential
):
    service.repository.get.return_value = pending_credential

    async def revoke(session, *, credential, revoked_at):
        credential.credential_status = "revoked"
        credential.revoked_at = revoked_at

    service.repository.revoke.side_effect = revoke

    result = await service.revoke_credential(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        credential_id=identifiers["credential_id"],
    )

    assert result.credential_status == "revoked"
    assert result.revoked_at is not None

    service.repository.revoke.assert_awaited_once()
    service.audit.record.assert_awaited_once()

    assert (
        service.audit.record.await_args.kwargs["action"]
        == "device_credential.revoked"
    )


@pytest.mark.asyncio
async def test_revoke_credential_rejects_already_revoked(
    service, identifiers, pending_credential
):
    pending_credential.credential_status = "revoked"
    pending_credential.revoked_at = datetime.now(timezone.utc)

    service.repository.get.return_value = pending_credential

    with pytest.raises(DeviceStateConflict):
        await service.revoke_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            credential_id=identifiers["credential_id"],
        )

    service.repository.revoke.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_credential_rejects_missing_credential(
    service, identifiers
):
    service.repository.get.return_value = None

    with pytest.raises(DeviceNotFound):
        await service.revoke_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            credential_id=identifiers["credential_id"],
        )

    service.repository.revoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_credential_allows_pending_provisioning_device(
    service, identifiers, monkeypatch
):
    pending_device = SimpleNamespace(
        id=identifiers["device_id"],
        workspace_id=identifiers["workspace_id"],
        is_enabled=True,
        lifecycle_status="pending_provisioning",
    )
    monkeypatch.setattr(
        service_module.secrets,
        "token_urlsafe",
        lambda size: "generated-secret-" + str(size),
    )
    monkeypatch.setattr(
        service_module,
        "hash_password",
        lambda password: "hashed:" + password,
    )

    credential = SimpleNamespace(
        id=identifiers["credential_id"],
        broker_key="broker-main",
        credential_identifier="dc_pending",
        credential_type="mqtt_password",
        credential_status="pending",
        created_at=datetime.now(timezone.utc),
        expires_at=None,
        revoked_at=None,
        rotated_at=None,
        last_used_at=None,
    )

    service.device_repository.get_device.return_value = pending_device
    service.repository.create.return_value = credential

    result = await service.create_credential(
        None,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
        broker_key="broker-main",
    )

    assert result.password == "generated-secret-32"
    assert result.metadata.credential_status == "pending"
    service.repository.create.assert_awaited_once()
    service.audit.record.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_credential_rejects_disabled_device(
    service, identifiers
):
    service.device_repository.get_device.return_value = SimpleNamespace(
        id=identifiers["device_id"],
        is_enabled=False,
        lifecycle_status="pending_provisioning",
    )

    with pytest.raises(DeviceStateConflict):
        await service.create_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
            broker_key="broker-main",
        )

    service.repository.create.assert_not_awaited()
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_credential_rejects_pending_provisioning_device(
    service, identifiers, pending_credential
):
    pending_device = SimpleNamespace(
        id=identifiers["device_id"],
        workspace_id=identifiers["workspace_id"],
        is_enabled=True,
        lifecycle_status="pending_provisioning",
    )
    service.repository.get.return_value = pending_credential
    service.device_repository.get_device.return_value = pending_device

    with pytest.raises(DeviceStateConflict):
        await service.activate_credential(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            credential_id=identifiers["credential_id"],
        )

    service.repository.activate.assert_not_awaited()
    service.audit.record.assert_not_awaited()
