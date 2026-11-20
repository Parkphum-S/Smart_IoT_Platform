from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import hashlib

import pytest

from app.modules.devices.services import device_enrollment_service as module
from app.modules.devices.services.device_enrollment_service import (
    DeviceEnrollmentService,
)
from app.modules.devices.services.exceptions import DeviceEnrollmentFailed


TOKEN = "bootstrap-test-secret"
PASSWORD = "Enrollment-Test-Password"
NOW = datetime.now(timezone.utc)


@pytest.fixture
def context():
    workspace_id = uuid4()
    device_id = uuid4()
    token_id = uuid4()
    credential_id = uuid4()

    device = SimpleNamespace(
        id=device_id,
        workspace_id=workspace_id,
        is_enabled=True,
        lifecycle_status="pending_provisioning",
    )

    token = SimpleNamespace(
        id=token_id,
        workspace_id=workspace_id,
        device_id=device_id,
        token_hash=hashlib.sha256(TOKEN.encode()).hexdigest(),
        expires_at=NOW + timedelta(minutes=15),
        consumed_at=None,
        revoked_at=None,
    )

    credential = SimpleNamespace(
        id=credential_id,
        workspace_id=workspace_id,
        device_id=device_id,
        broker_key="broker-main",
        credential_identifier="dc_test123",
        credential_type="mqtt_password",
        credential_status="pending",
        secret_hash="$argon2id$test-hash",
        secret_reference=None,
        expires_at=NOW + timedelta(minutes=15),
    )

    service = DeviceEnrollmentService()

    service.bootstrap_repository = SimpleNamespace(
        get_for_validation=AsyncMock(return_value=token),
        get_for_enrollment=AsyncMock(return_value=token),
        consume=AsyncMock(),
    )

    service.credential_repository = SimpleNamespace(
        get_for_enrollment=AsyncMock(return_value=credential),
        activate=AsyncMock(),
    )

    service.device_repository = SimpleNamespace(
        lock_workspace=AsyncMock(),
        get_device=AsyncMock(return_value=device),
        activate_after_enrollment=AsyncMock(),
    )

    service.audit = SimpleNamespace(record=AsyncMock())

    return SimpleNamespace(
        service=service,
        device=device,
        token=token,
        credential=credential,
        workspace_id=workspace_id,
        device_id=device_id,
        credential_id=credential_id,
    )


@pytest.fixture
def valid_password(monkeypatch):
    monkeypatch.setattr(
        module,
        "verify_password",
        lambda password, password_hash: (
            password == PASSWORD
            and password_hash == "$argon2id$test-hash"
        ),
    )


@pytest.mark.asyncio
async def test_enroll_device_success(context, valid_password):
    async def consume(session, *, token, consumed_at):
        token.consumed_at = consumed_at

    async def activate_credential(session, *, credential):
        credential.credential_status = "active"

    async def activate_device(session, *, device):
        device.lifecycle_status = "active"
        return device

    context.service.bootstrap_repository.consume.side_effect = consume
    context.service.credential_repository.activate.side_effect = (
        activate_credential
    )
    context.service.device_repository.activate_after_enrollment.side_effect = (
        activate_device
    )

    result = await context.service.enroll_device(
        None,
        bootstrap_token=TOKEN,
        broker_key="broker-main",
        credential_identifier="dc_test123",
        password=PASSWORD,
    )

    assert result.device_id == context.device_id
    assert result.credential_id == context.credential_id
    assert result.lifecycle_status == "active"
    assert result.credential_status == "active"

    context.service.device_repository.lock_workspace.assert_awaited_once()
    context.service.device_repository.get_device.assert_awaited_once()
    context.service.bootstrap_repository.get_for_enrollment.assert_awaited_once()
    context.service.credential_repository.get_for_enrollment.assert_awaited_once()

    context.service.bootstrap_repository.consume.assert_awaited_once()
    context.service.credential_repository.activate.assert_awaited_once()
    context.service.device_repository.activate_after_enrollment.assert_awaited_once()

    audit = context.service.audit.record.await_args.kwargs

    assert audit["actor_type"] == "device"
    assert audit["actor_id"] == context.device_id
    assert audit["action"] == "device.enrolled"

    audit_text = repr(audit)
    assert TOKEN not in audit_text
    assert PASSWORD not in audit_text
    assert context.token.token_hash not in audit_text
    assert "dc_test123" not in audit_text


@pytest.mark.asyncio
async def test_enrollment_uses_canonical_lock_order(
    context, valid_password
):
    from unittest.mock import Mock, call

    order = Mock()
    order.attach_mock(
        context.service.device_repository.lock_workspace, "workspace"
    )
    order.attach_mock(
        context.service.device_repository.get_device, "device"
    )
    order.attach_mock(
        context.service.bootstrap_repository.get_for_enrollment, "token"
    )
    order.attach_mock(
        context.service.credential_repository.get_for_enrollment,
        "credential",
    )

    await context.service.enroll_device(
        None,
        bootstrap_token=TOKEN,
        broker_key="broker-main",
        credential_identifier="dc_test123",
        password=PASSWORD,
    )

    assert order.mock_calls == [
        call.workspace(None, workspace_id=context.workspace_id),
        call.device(
            None,
            workspace_id=context.workspace_id,
            device_id=context.device_id,
            for_update=True,
        ),
        call.token(
            None,
            workspace_id=context.workspace_id,
            token_id=context.token.id,
            for_update=True,
        ),
        call.credential(
            None,
            workspace_id=context.workspace_id,
            device_id=context.device_id,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            for_update=True,
        ),
    ]


@pytest.mark.asyncio
async def test_invalid_bootstrap_token_fails(context):
    context.service.bootstrap_repository.get_for_validation.return_value = None

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )

    context.service.device_repository.lock_workspace.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("is_enabled", False),
        ("lifecycle_status", "active"),
        ("lifecycle_status", "disabled"),
    ],
)
async def test_ineligible_device_fails(
    context, valid_password, field, value
):
    setattr(context.device, field, value)

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )

    context.service.credential_repository.activate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("credential_status", "active"),
        ("credential_status", "revoked"),
        ("credential_type", "api_key"),
        ("secret_hash", None),
        ("secret_reference", "vault://secret"),
    ],
)
async def test_ineligible_credential_fails(
    context, valid_password, field, value
):
    setattr(context.credential, field, value)

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )

    context.service.bootstrap_repository.consume.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_password_fails(context, valid_password):
    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password="Wrong-Password",
        )

    context.service.bootstrap_repository.consume.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_token_fails(context, valid_password):
    context.token.expires_at = NOW - timedelta(seconds=1)

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )

    context.service.bootstrap_repository.consume.assert_not_awaited()


@pytest.mark.asyncio
async def test_consumed_token_fails(context, valid_password):
    context.token.consumed_at = NOW

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )


@pytest.mark.asyncio
async def test_revoked_token_fails(context, valid_password):
    context.token.revoked_at = NOW

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )


@pytest.mark.asyncio
async def test_expired_credential_fails(context, valid_password):
    context.credential.expires_at = NOW - timedelta(seconds=1)

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )


@pytest.mark.asyncio
async def test_credential_wrong_device_fails(context, valid_password):
    context.credential.device_id = uuid4()

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )


@pytest.mark.asyncio
async def test_device_not_found_fails(context):
    context.service.device_repository.get_device.return_value = None

    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )


@pytest.mark.asyncio
async def test_audit_failure_propagates(context, valid_password):
    context.service.audit.record.side_effect = RuntimeError("audit failure")

    with pytest.raises(RuntimeError, match="audit failure"):
        await context.service.enroll_device(
            None,
            bootstrap_token=TOKEN,
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )


@pytest.mark.asyncio
async def test_invalid_input_fails_before_database_access(context):
    with pytest.raises(DeviceEnrollmentFailed):
        await context.service.enroll_device(
            None,
            bootstrap_token="",
            broker_key="broker-main",
            credential_identifier="dc_test123",
            password=PASSWORD,
        )

    context.service.bootstrap_repository.get_for_validation.assert_not_awaited()
