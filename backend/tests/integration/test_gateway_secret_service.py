"""Integration tests for encrypted gateway secret management."""

import asyncio
import base64

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.infrastructure.security.encryption import (
    EncryptionError,
    GatewaySecretEncryption,
)
from app.modules.devices.models import (
    DeviceGateway,
    DeviceGatewaySecret,
)
from app.modules.devices.services.exceptions import (
    DevicePermissionDenied,
    GatewayNotFound,
    GatewaySecretAlreadyExists,
    GatewaySecretEncryptionUnavailable,
    GatewaySecretNotFound,
)
from app.modules.devices.services.gateway_secret_service import (
    GatewaySecretService,
)
from app.modules.monitoring.models import AuditLog
from app.modules.users.models import WorkspaceMember
from factories import create_user, create_workspace_with_owner


TEST_KEY = bytes(range(32))
TEST_KEY_BASE64 = base64.b64encode(TEST_KEY).decode("ascii")


@pytest.fixture
def secret_settings():
    current = get_settings()
    return Settings(
        _env_file=None,
        app_env="testing",
        database_url=current.database_url,
        gateway_encryption_key=SecretStr(TEST_KEY_BASE64),
        gateway_encryption_key_version="v1",
    )


def create_service(secret_settings):
    return GatewaySecretService(settings=secret_settings)


async def create_gateway(session, workspace, device_type):
    from factories import create_device

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
    return device


async def create_secret(
    service,
    session,
    owner,
    workspace,
    gateway,
    name="mqtt_password",
    value="integration-private-value",
):
    return await service.create_secret(
        session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        gateway_device_id=gateway.id,
        secret_name=name,
        secret_value=value,
    )


@pytest.mark.asyncio
async def test_create_secret_encrypts_value_and_audits_metadata(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    service = create_service(secret_settings)
    plaintext = "private-gateway-password"

    metadata = await create_secret(
        service,
        db_session,
        owner,
        workspace,
        gateway,
        value=plaintext,
    )

    stored = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace.id,
            DeviceGatewaySecret.gateway_device_id == gateway.id,
            DeviceGatewaySecret.secret_name == "mqtt_password",
        )
    )

    assert metadata.secret_name == "mqtt_password"
    assert not hasattr(metadata, "ciphertext")
    assert not hasattr(metadata, "secret_value")

    assert stored is not None
    assert stored.ciphertext != plaintext
    assert plaintext not in stored.ciphertext
    assert stored.key_version == "v1"

    encryption = GatewaySecretEncryption.from_base64(TEST_KEY_BASE64, "v1")

    assert encryption.decrypt(
        stored.ciphertext,
        stored.key_version,
        workspace_id=str(workspace.id),
        gateway_id=str(gateway.id),
    ) == plaintext

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "device.gateway_secret.created",
            AuditLog.resource_id == gateway.id,
        )
    )

    assert audit is not None
    assert audit.details == {"secret_name": "mqtt_password"}
    assert plaintext not in str(audit.details)
    assert stored.ciphertext not in str(audit.details)


@pytest.mark.asyncio
async def test_list_secrets_returns_metadata_only(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)
    service = create_service(secret_settings)

    await create_secret(service, db_session, owner, workspace, gateway)

    result = await service.list_secrets(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        gateway_device_id=gateway.id,
    )

    assert len(result) == 1
    assert result[0].secret_name == "mqtt_password"
    assert not hasattr(result[0], "ciphertext")
    assert not hasattr(result[0], "secret_value")


@pytest.mark.asyncio
async def test_update_secret_reencrypts_value(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)
    service = create_service(secret_settings)

    await create_secret(service, db_session, owner, workspace, gateway)

    stored = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace.id,
            DeviceGatewaySecret.gateway_device_id == gateway.id,
        )
    )
    old_ciphertext = stored.ciphertext

    metadata = await service.update_secret(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        gateway_device_id=gateway.id,
        secret_name="mqtt_password",
        secret_value="updated-private-value",
    )

    assert metadata.secret_name == "mqtt_password"
    assert stored.ciphertext != old_ciphertext

    encryption = GatewaySecretEncryption.from_base64(TEST_KEY_BASE64, "v1")

    assert encryption.decrypt(
        stored.ciphertext,
        stored.key_version,
        workspace_id=str(workspace.id),
        gateway_id=str(gateway.id),
    ) == "updated-private-value"


@pytest.mark.asyncio
async def test_delete_secret_removes_record(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)
    service = create_service(secret_settings)

    await create_secret(service, db_session, owner, workspace, gateway)

    await service.delete_secret(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        gateway_device_id=gateway.id,
        secret_name="mqtt_password",
    )

    stored = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace.id,
            DeviceGatewaySecret.gateway_device_id == gateway.id,
        )
    )

    assert stored is None

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "device.gateway_secret.deleted",
            AuditLog.resource_id == gateway.id,
        )
    )
    assert audit is not None
    assert audit.details == {"secret_name": "mqtt_password"}


@pytest.mark.asyncio
async def test_update_missing_secret_is_rejected(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    with pytest.raises(GatewaySecretNotFound):
        await create_service(secret_settings).update_secret(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            gateway_device_id=gateway.id,
            secret_name="missing",
            secret_value="value",
        )


@pytest.mark.asyncio
async def test_delete_missing_secret_is_rejected(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    with pytest.raises(GatewaySecretNotFound):
        await create_service(secret_settings).delete_secret(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            gateway_device_id=gateway.id,
            secret_name="missing",
        )


@pytest.mark.asyncio
async def test_foreign_workspace_gateway_is_not_accessible(
    db_session,
    secret_settings,
):
    workspace_a, owner_a, _ = await create_workspace_with_owner(db_session)
    workspace_b, _, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    foreign_gateway = await create_gateway(
        db_session,
        workspace_b,
        device_type,
    )

    with pytest.raises(GatewayNotFound):
        await create_service(secret_settings).list_secrets(
            db_session,
            actor_id=owner_a.id,
            workspace_id=workspace_a.id,
            gateway_device_id=foreign_gateway.id,
        )


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        ("admin", True),
        ("operator", False),
        ("viewer", False),
    ],
)
@pytest.mark.asyncio
async def test_create_secret_respects_workspace_role(
    db_session,
    secret_settings,
    role,
    allowed,
):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    actor = await create_user(db_session)

    await create_membership_for_role(
        db_session,
        workspace,
        actor,
        role,
    )

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    service = create_service(secret_settings)

    if allowed:
        await create_secret(
            service,
            db_session,
            actor,
            workspace,
            gateway,
        )
    else:
        with pytest.raises(DevicePermissionDenied):
            await create_secret(
                service,
                db_session,
                actor,
                workspace,
                gateway,
            )


async def create_membership_for_role(session, workspace, actor, role):
    from factories import create_membership

    return await create_membership(
        session,
        workspace=workspace,
        user=actor,
        role=role,
    )


@pytest.mark.parametrize("role", ["operator", "viewer"])
@pytest.mark.asyncio
async def test_read_secret_metadata_allowed_for_read_roles(
    db_session,
    secret_settings,
    role,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    actor = await create_user(db_session)

    await create_membership_for_role(
        db_session,
        workspace,
        actor,
        role,
    )

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)
    service = create_service(secret_settings)

    await create_secret(service, db_session, owner, workspace, gateway)

    result = await service.list_secrets(
        db_session,
        actor_id=actor.id,
        workspace_id=workspace.id,
        gateway_device_id=gateway.id,
    )

    assert len(result) == 1


@pytest.mark.asyncio
async def test_non_member_cannot_read_secrets(
    db_session,
    secret_settings,
):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    outsider = await create_user(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    with pytest.raises(DevicePermissionDenied):
        await create_service(secret_settings).list_secrets(
            db_session,
            actor_id=outsider.id,
            workspace_id=workspace.id,
            gateway_device_id=gateway.id,
        )


@pytest.mark.asyncio
async def test_encryption_rejects_wrong_workspace_and_gateway_context(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)
    service = create_service(secret_settings)

    await create_secret(service, db_session, owner, workspace, gateway)

    stored = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace.id,
            DeviceGatewaySecret.gateway_device_id == gateway.id,
        )
    )

    encryption = GatewaySecretEncryption.from_base64(TEST_KEY_BASE64, "v1")

    with pytest.raises(EncryptionError):
        encryption.decrypt(
            stored.ciphertext,
            stored.key_version,
            workspace_id="different-workspace",
            gateway_id=str(gateway.id),
        )

    with pytest.raises(EncryptionError):
        encryption.decrypt(
            stored.ciphertext,
            stored.key_version,
            workspace_id=str(workspace.id),
            gateway_id="different-gateway",
        )


@pytest.mark.asyncio
async def test_missing_encryption_key_prevents_secret_creation(db_session):
    current = get_settings()
    settings = Settings(
        _env_file=None,
        app_env="testing",
        database_url=current.database_url,
        gateway_encryption_key=None,
    )

    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    with pytest.raises(GatewaySecretEncryptionUnavailable):
        await create_secret(
            create_service(settings),
            db_session,
            owner,
            workspace,
            gateway,
        )

    stored = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace.id,
            DeviceGatewaySecret.gateway_device_id == gateway.id,
        )
    )
    assert stored is None


@pytest.mark.asyncio
async def test_secret_and_audit_rollback_together(
    db_session,
    secret_settings,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)

    from factories import create_device_type

    device_type = await create_device_type(db_session)
    gateway = await create_gateway(db_session, workspace, device_type)

    nested = await db_session.begin_nested()

    await create_secret(
        create_service(secret_settings),
        db_session,
        owner,
        workspace,
        gateway,
    )

    await nested.rollback()

    stored = await db_session.scalar(
        select(DeviceGatewaySecret).where(
            DeviceGatewaySecret.workspace_id == workspace.id,
            DeviceGatewaySecret.gateway_device_id == gateway.id,
        )
    )

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "device.gateway_secret.created",
            AuditLog.resource_id == gateway.id,
        )
    )

    assert stored is None
    assert audit is None


@pytest.mark.asyncio
async def test_concurrent_duplicate_secret_creation_is_serialized(
    gateway_secret_concurrency_context,
    secret_settings,
):
    context = gateway_secret_concurrency_context
    factory = context["session_factory"]

    workspace_id = context["workspace_id"]
    owner_id = context["owner_id"]
    gateway_id = context["gateway_device_id"]

    def service_without_persistent_audit():
        service = create_service(secret_settings)

        async def skip_audit(*args, **kwargs):
            return None

        service.audit.record = skip_audit
        return service

    first_session = factory()
    first_transaction = await first_session.begin()

    try:
        await service_without_persistent_audit().create_secret(
            first_session,
            actor_id=owner_id,
            workspace_id=workspace_id,
            gateway_device_id=gateway_id,
            secret_name="concurrent_secret",
            secret_value="first-value",
        )

        second_started = asyncio.Event()

        async def competing_create():
            async with factory() as second_session:
                async with second_session.begin():
                    second_started.set()
                    return await service_without_persistent_audit().create_secret(
                        second_session,
                        actor_id=owner_id,
                        workspace_id=workspace_id,
                        gateway_device_id=gateway_id,
                        secret_name="concurrent_secret",
                        secret_value="second-value",
                    )

        second_task = asyncio.create_task(competing_create())

        await asyncio.wait_for(second_started.wait(), timeout=5)

        done, _ = await asyncio.wait({second_task}, timeout=0.15)
        assert not done, "Second create should wait for the workspace lock."

        async with factory() as probe_session:
            lock_available = await probe_session.scalar(
                select(
                    func.pg_try_advisory_xact_lock(
                        func.hashtextextended(str(workspace_id), 0)
                    )
                )
            )

        assert lock_available is False

        await first_transaction.commit()

        with pytest.raises(GatewaySecretAlreadyExists):
            await asyncio.wait_for(second_task, timeout=5)

    finally:
        if first_transaction.is_active:
            await first_transaction.rollback()
        await first_session.close()
