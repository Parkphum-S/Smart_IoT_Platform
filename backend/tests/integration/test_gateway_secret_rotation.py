"""Integration tests for internal gateway secret key rotation."""

import base64
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.infrastructure.security.encryption import (
    EncryptionError,
    GatewaySecretEncryption,
)
from app.modules.devices.models import DeviceGateway, DeviceGatewaySecret
from app.modules.devices.services.gateway_secret_rotation_service import (
    GatewaySecretRotationService,
)
from scripts.gateway_secret_rotation import (
    check_key_retirement,
    rotate_workspace,
)
from app.modules.devices.services.gateway_secret_service import (
    GatewaySecretService,
)
from factories import create_device_type, create_workspace_with_owner


TEST_KEY = bytes(range(32))
TEST_KEY_BASE64 = base64.b64encode(TEST_KEY).decode("ascii")
KEY_V2 = bytes(reversed(range(32)))
KEY_V2_BASE64 = base64.b64encode(KEY_V2).decode("ascii")


@pytest.fixture
def rotation_settings():
    current = get_settings()
    return Settings(
        _env_file=None,
        app_env="testing",
        database_url=current.database_url,
        gateway_encryption_keys={
            "v1": SecretStr(TEST_KEY_BASE64),
            "v2": SecretStr(KEY_V2_BASE64),
        },
        gateway_encryption_key_version="v2",
    )


async def make_old_secrets(session, count=3):
    from factories import create_device

    workspace, owner, _ = await create_workspace_with_owner(session)
    device_type = await create_device_type(session)
    device = await create_device(
        session,
        workspace=workspace,
        device_type=device_type,
    )

    gateway = DeviceGateway(
        device_id=device.id,
        workspace_id=workspace.id,
        gateway_type="generic",
        adapter_key="integration",
        configuration={},
    )
    session.add(gateway)
    await session.flush()

    old_settings = Settings(
        _env_file=None,
        app_env="testing",
        database_url=get_settings().database_url,
        gateway_encryption_key=SecretStr(TEST_KEY_BASE64),
        gateway_encryption_key_version="v1",
    )
    old_service = GatewaySecretService(settings=old_settings)

    for index in range(count):
        await old_service.create_secret(
            session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            gateway_device_id=gateway.device_id,
            secret_name=f"secret_{index:03d}",
            secret_value=f"private-value-{index}",
        )

    return workspace, gateway


@pytest.mark.asyncio
async def test_rotation_processes_secrets_in_bounded_batches(
    db_session,
    rotation_settings,
):
    workspace, gateway = await make_old_secrets(db_session, count=3)
    service = GatewaySecretRotationService(rotation_settings)

    # The integration fixture owns an outer rollback-only transaction.
    # These calls verify bounded progression, not independent DB commits.
    first = await service.rotate_workspace_batch(
        db_session,
        workspace_id=workspace.id,
        batch_size=2,
    )
    assert first.rotated_count == 2

    second = await service.rotate_workspace_batch(
        db_session,
        workspace_id=workspace.id,
        batch_size=2,
    )
    assert second.rotated_count == 1

    third = await service.rotate_workspace_batch(
        db_session,
        workspace_id=workspace.id,
        batch_size=2,
    )
    assert third.rotated_count == 0

    records = list(
        (
            await db_session.scalars(
                select(DeviceGatewaySecret).where(
                    DeviceGatewaySecret.workspace_id == workspace.id,
                    DeviceGatewaySecret.gateway_device_id == gateway.device_id,
                )
            )
        ).all()
    )

    assert len(records) == 3
    assert {record.key_version for record in records} == {"v2"}

    new_encryption = GatewaySecretEncryption(KEY_V2, "v2")
    for record in records:
        index = int(record.secret_name[-3:])
        assert new_encryption.decrypt(
            record.ciphertext,
            record.key_version,
            workspace_id=str(workspace.id),
            gateway_id=str(gateway.device_id),
        ) == f"private-value-{index}"


@pytest.mark.asyncio
async def test_rotation_is_scoped_to_requested_workspace(
    db_session,
    rotation_settings,
):
    workspace_a, gateway_a = await make_old_secrets(db_session, count=1)
    workspace_b, gateway_b = await make_old_secrets(db_session, count=1)

    service = GatewaySecretRotationService(rotation_settings)
    result = await service.rotate_workspace_batch(
        db_session,
        workspace_id=workspace_a.id,
    )

    assert result.rotated_count == 1

    record_a = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace_a.id,
            DeviceGatewaySecret.gateway_device_id == gateway_a.device_id,
        )
    )
    record_b = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace_b.id,
            DeviceGatewaySecret.gateway_device_id == gateway_b.device_id,
        )
    )

    assert record_a is not None and record_a.key_version == "v2"
    assert record_b is not None and record_b.key_version == "v1"


@pytest.mark.asyncio
async def test_rotation_batch_does_not_partially_mutate_on_decryption_failure(
    db_session,
    rotation_settings,
):
    workspace, gateway = await make_old_secrets(db_session, count=2)

    records = list(
        (
            await db_session.scalars(
                select(DeviceGatewaySecret)
                .where(
                    DeviceGatewaySecret.workspace_id == workspace.id,
                    DeviceGatewaySecret.gateway_device_id == gateway.device_id,
                )
                .order_by(DeviceGatewaySecret.secret_name)
            )
        ).all()
    )
    first, second = records
    original_first_ciphertext = first.ciphertext

    # Corrupt the second row before entering the batch savepoint.
    second.ciphertext = "invalid-ciphertext"
    await db_session.flush()

    service = GatewaySecretRotationService(rotation_settings)

    with pytest.raises(EncryptionError):
        async with db_session.begin_nested():
            await service.rotate_workspace_batch(
                db_session,
                workspace_id=workspace.id,
                batch_size=10,
            )

    await db_session.refresh(first)
    assert first.key_version == "v1"
    assert first.ciphertext == original_first_ciphertext


@pytest.mark.asyncio
@pytest.mark.parametrize("batch_size", [0, -1, 1001, True, 1.5])
async def test_rotation_rejects_invalid_batch_size(batch_size):
    service = GatewaySecretRotationService()

    with pytest.raises(ValueError, match="batch_size"):
        await service.rotate_workspace_batch(
            None,
            workspace_id=uuid4(),
            batch_size=batch_size,
        )



async def _create_committed_old_secrets(context, count=3):
    """Create v1 secrets using the fixture's independent committed sessions."""
    factory = context["session_factory"]

    old_settings = Settings(
        _env_file=None,
        app_env="testing",
        database_url=get_settings().database_url,
        gateway_encryption_key=SecretStr(TEST_KEY_BASE64),
        gateway_encryption_key_version="v1",
    )
    old_service = GatewaySecretService(settings=old_settings)

    async with factory() as session:
        async with session.begin():
            for index in range(count):
                await old_service.create_secret(
                    session,
                    actor_id=context["owner_id"],
                    workspace_id=context["workspace_id"],
                    gateway_device_id=context["gateway_device_id"],
                    secret_name=f"cli_secret_{index:03d}",
                    secret_value=f"cli-private-value-{index}",
                )


@pytest.mark.asyncio
async def test_rotation_cli_commits_each_batch_to_independent_sessions(
    gateway_secret_concurrency_context,
    rotation_settings,
):
    context = gateway_secret_concurrency_context
    factory = context["session_factory"]
    await _create_committed_old_secrets(context, count=3)

    service = GatewaySecretRotationService(rotation_settings)
    messages = []

    total = await rotate_workspace(
        factory,
        service,
        context["workspace_id"],
        batch_size=1,
        emit=messages.append,
    )

    assert total == 3
    assert len(messages) == 4  # Three committed batches plus final empty batch.
    assert all("Batch committed:" in message for message in messages)

    async with factory() as session:
        records = list(
            (
                await session.scalars(
                    select(DeviceGatewaySecret).where(
                        DeviceGatewaySecret.workspace_id
                        == context["workspace_id"],
                        DeviceGatewaySecret.gateway_device_id
                        == context["gateway_device_id"],
                        DeviceGatewaySecret.secret_name.like("cli_secret_%"),
                    )
                )
            ).all()
        )

    assert len(records) == 3
    assert {record.key_version for record in records} == {"v2"}

    encryption = GatewaySecretEncryption(KEY_V2, "v2")
    for record in records:
        index = int(record.secret_name[-3:])
        assert encryption.decrypt(
            record.ciphertext,
            record.key_version,
            workspace_id=str(context["workspace_id"]),
            gateway_id=str(context["gateway_device_id"]),
        ) == f"cli-private-value-{index}"


@pytest.mark.asyncio
async def test_rotation_cli_rolls_back_failed_batch_but_keeps_prior_commit(
    gateway_secret_concurrency_context,
    rotation_settings,
):
    context = gateway_secret_concurrency_context
    factory = context["session_factory"]
    await _create_committed_old_secrets(context, count=3)

    delegate = GatewaySecretRotationService(rotation_settings)

    class FailAfterSecondBatch:
        calls = 0

        async def rotate_workspace_batch(self, session, **kwargs):
            self.calls += 1
            result = await delegate.rotate_workspace_batch(session, **kwargs)

            if self.calls == 2:
                # Simulate an error after ORM rows have been changed and flushed.
                raise RuntimeError("simulated batch failure")

            return result

    service = FailAfterSecondBatch()

    with pytest.raises(RuntimeError, match="simulated batch failure"):
        await rotate_workspace(
            factory,
            service,
            context["workspace_id"],
            batch_size=1,
            emit=lambda _: None,
        )

    async with factory() as session:
        records = list(
            (
                await session.scalars(
                    select(DeviceGatewaySecret).where(
                        DeviceGatewaySecret.workspace_id
                        == context["workspace_id"],
                        DeviceGatewaySecret.gateway_device_id
                        == context["gateway_device_id"],
                        DeviceGatewaySecret.secret_name.like("cli_secret_%"),
                    )
                )
            ).all()
        )

    assert len(records) == 3
    versions = [record.key_version for record in records]
    assert versions.count("v2") == 1
    assert versions.count("v1") == 2


@pytest.mark.asyncio
async def test_key_retirement_check_uses_explicit_configured_versions(
    gateway_secret_concurrency_context,
    rotation_settings,
):
    context = gateway_secret_concurrency_context
    factory = context["session_factory"]
    await _create_committed_old_secrets(context, count=2)

    count = await check_key_retirement(
        factory,
        retire_version="v1",
        active_version="v2",
        configured_versions={"v1", "v2"},
    )
    assert count == 2

    with pytest.raises(RuntimeError, match="missing from configuration"):
        await check_key_retirement(
            factory,
            retire_version="v1",
            active_version="v2",
            configured_versions={"v2"},
        )

    with pytest.raises(ValueError, match="active encryption key"):
        await check_key_retirement(
            factory,
            retire_version="v2",
            active_version="v2",
            configured_versions={"v1", "v2"},
        )
