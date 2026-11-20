from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.devices.services.device_service import DeviceService
from app.modules.devices.services.exceptions import DeviceStateConflict


@pytest.fixture
def service():
    instance = DeviceService()
    instance.repository = SimpleNamespace(
        lock_workspace=AsyncMock(),
        get_device=AsyncMock(),
    )
    instance.authorization = SimpleNamespace(
        authorize=AsyncMock(),
    )
    instance.audit = SimpleNamespace(
        record=AsyncMock(),
    )
    return instance


@pytest.fixture
def session():
    return SimpleNamespace(flush=AsyncMock())


@pytest.fixture
def identifiers():
    return {
        "actor_id": uuid4(),
        "workspace_id": uuid4(),
        "device_id": uuid4(),
    }


@pytest.mark.asyncio
async def test_management_cannot_activate_pending_device(
    service, identifiers, session
):
    device = SimpleNamespace(
        id=identifiers["device_id"],
        lifecycle_status="pending_provisioning",
        is_enabled=True,
    )
    service.repository.get_device.return_value = device

    with pytest.raises(
        DeviceStateConflict,
        match="complete enrollment before activation",
    ):
        await service.change_lifecycle(
            None,
            actor_id=identifiers["actor_id"],
            workspace_id=identifiers["workspace_id"],
            device_id=identifiers["device_id"],
            new_status="active",
        )

    assert device.lifecycle_status == "pending_provisioning"
    assert device.is_enabled is True
    service.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_pending_device_can_be_disabled(
    service, identifiers, session
):
    device = SimpleNamespace(
        id=identifiers["device_id"],
        lifecycle_status="pending_provisioning",
        is_enabled=True,
    )
    service.repository.get_device.return_value = device

    result = await service.change_lifecycle(
        session,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
        new_status="disabled",
    )

    assert result is device
    assert device.lifecycle_status == "disabled"
    assert device.is_enabled is False
    service.audit.record.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_device_can_still_be_reactivated(
    service, identifiers, session
):
    device = SimpleNamespace(
        id=identifiers["device_id"],
        lifecycle_status="disabled",
        is_enabled=False,
    )
    service.repository.get_device.return_value = device

    result = await service.change_lifecycle(
        session,
        actor_id=identifiers["actor_id"],
        workspace_id=identifiers["workspace_id"],
        device_id=identifiers["device_id"],
        new_status="active",
    )

    assert result is device
    assert device.lifecycle_status == "active"
    assert device.is_enabled is True
    service.audit.record.assert_awaited_once()
