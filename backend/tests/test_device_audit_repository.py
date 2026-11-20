from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.modules.devices.services.audit_repository import (
    DeviceAuditRepository,
)


@pytest.fixture
def mock_session():
    return SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_record_defaults_to_user_actor(mock_session):
    workspace_id = uuid4()
    actor_id = uuid4()
    resource_id = uuid4()

    result = await DeviceAuditRepository().record(
        mock_session,
        workspace_id=workspace_id,
        actor_id=actor_id,
        action="device.updated",
        resource_type="device",
        resource_id=resource_id,
    )

    assert result.actor_type == "user"
    assert result.actor_id == actor_id
    assert result.workspace_id == workspace_id
    assert result.resource_id == resource_id
    assert result.details == {}
    mock_session.add.assert_called_once_with(result)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_supports_device_actor(mock_session):
    device_id = uuid4()

    result = await DeviceAuditRepository().record(
        mock_session,
        workspace_id=uuid4(),
        actor_id=device_id,
        actor_type="device",
        action="device.enrolled",
        resource_type="device",
        resource_id=device_id,
    )

    assert result.actor_type == "device"
    assert result.actor_id == device_id
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_supports_system_actor_without_id(mock_session):
    result = await DeviceAuditRepository().record(
        mock_session,
        workspace_id=uuid4(),
        actor_id=None,
        actor_type="system",
        action="device.maintenance",
        resource_type="device",
        resource_id=uuid4(),
    )

    assert result.actor_type == "system"
    assert result.actor_id is None
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_rejects_unsupported_actor_type(mock_session):
    with pytest.raises(ValueError, match="Unsupported audit actor"):
        await DeviceAuditRepository().record(
            mock_session,
            workspace_id=uuid4(),
            actor_id=uuid4(),
            actor_type="unknown",
            action="device.updated",
            resource_type="device",
            resource_id=uuid4(),
        )

    mock_session.add.assert_not_called()
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_rejects_user_actor_without_id(mock_session):
    with pytest.raises(ValueError, match="require an actor ID"):
        await DeviceAuditRepository().record(
            mock_session,
            workspace_id=uuid4(),
            actor_id=None,
            action="device.updated",
            resource_type="device",
            resource_id=uuid4(),
        )

    mock_session.add.assert_not_called()
    mock_session.flush.assert_not_awaited()
