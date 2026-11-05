"""Regression tests: unauthorized users must never acquire workspace locks."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.devices.services.device_service import DeviceService
from app.modules.devices.services.exceptions import DevicePermissionDenied
from app.modules.devices.services.gateway_service import GatewayService
from app.modules.devices.services.gateway_secret_service import (
    GatewaySecretService,
)
from factories import create_user, create_workspace_with_owner


OPERATIONS = [
    "device.create",
    "device.update",
    "device.change_lifecycle",
    "gateway.register",
    "gateway.update",
    "gateway.assign",
    "gateway.remove",
    "secret.create",
    "secret.update",
    "secret.delete",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS)
async def test_non_member_is_rejected_before_workspace_lock(
    db_session,
    monkeypatch,
    operation,
):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    outsider = await create_user(db_session)

    device_service = DeviceService()
    gateway_service = GatewayService()
    secret_service = GatewaySecretService()

    if operation.startswith("device."):
        service = device_service
        lock_owner = service.repository
    elif operation.startswith("gateway."):
        service = gateway_service
        lock_owner = service.repository
    else:
        service = secret_service
        lock_owner = service.device_repository

    lock_spy = AsyncMock()
    monkeypatch.setattr(lock_owner, "lock_workspace", lock_spy)

    common = {
        "actor_id": outsider.id,
        "workspace_id": workspace.id,
    }

    if operation == "device.create":
        call = service.create_device(
            db_session,
            **common,
            device_type_id=uuid4(),
            device_uid="unauthorized-device",
            name="Unauthorized Device",
        )
    elif operation == "device.update":
        call = service.update_device(
            db_session,
            **common,
            device_id=uuid4(),
            changes={"name": "Unauthorized Update"},
        )
    elif operation == "device.change_lifecycle":
        call = service.change_lifecycle(
            db_session,
            **common,
            device_id=uuid4(),
            new_status="active",
        )
    elif operation == "gateway.register":
        call = service.register_gateway(
            db_session,
            **common,
            device_id=uuid4(),
            gateway_type="generic",
            adapter_key="unauthorized-adapter",
        )
    elif operation == "gateway.update":
        call = service.update_gateway(
            db_session,
            **common,
            device_id=uuid4(),
            gateway_type="modified",
        )
    elif operation == "gateway.assign":
        call = service.assign_gateway(
            db_session,
            **common,
            child_device_id=uuid4(),
            gateway_device_id=uuid4(),
        )
    elif operation == "gateway.remove":
        call = service.remove_gateway(
            db_session,
            **common,
            child_device_id=uuid4(),
        )
    elif operation == "secret.create":
        call = service.create_secret(
            db_session,
            **common,
            gateway_device_id=uuid4(),
            secret_name="test_secret",
            secret_value="test-value",
        )
    elif operation == "secret.update":
        call = service.update_secret(
            db_session,
            **common,
            gateway_device_id=uuid4(),
            secret_name="test_secret",
            secret_value="updated-value",
        )
    elif operation == "secret.delete":
        call = service.delete_secret(
            db_session,
            **common,
            gateway_device_id=uuid4(),
            secret_name="test_secret",
        )
    else:
        pytest.fail(f"Unknown operation: {operation}")

    with pytest.raises(DevicePermissionDenied):
        await call

    lock_spy.assert_not_awaited()
