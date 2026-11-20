from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.devices.services.device_repository import DeviceRepository


@pytest.fixture
def mock_session():
    session = SimpleNamespace(flush=AsyncMock())
    return session


@pytest.mark.asyncio
async def test_activate_after_enrollment_activates_pending_device(
    mock_session,
):
    device = SimpleNamespace(
        lifecycle_status="pending_provisioning",
        is_enabled=True,
    )

    result = await DeviceRepository().activate_after_enrollment(
        mock_session,
        device=device,
    )

    assert result is device
    assert device.lifecycle_status == "active"
    assert device.is_enabled is True
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_after_enrollment_rejects_active_device(
    mock_session,
):
    device = SimpleNamespace(
        lifecycle_status="active",
        is_enabled=True,
    )

    with pytest.raises(ValueError, match="not eligible"):
        await DeviceRepository().activate_after_enrollment(
            mock_session,
            device=device,
        )

    assert device.lifecycle_status == "active"
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_after_enrollment_rejects_disabled_device(
    mock_session,
):
    device = SimpleNamespace(
        lifecycle_status="pending_provisioning",
        is_enabled=False,
    )

    with pytest.raises(ValueError, match="not eligible"):
        await DeviceRepository().activate_after_enrollment(
            mock_session,
            device=device,
        )

    assert device.lifecycle_status == "pending_provisioning"
    assert device.is_enabled is False
    mock_session.flush.assert_not_awaited()
