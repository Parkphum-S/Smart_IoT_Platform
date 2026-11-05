"""Integration tests for device CRUD domain operations."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.devices.services.device_service import DeviceService
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    DeviceTypeNotFound,
)
from factories import (
    create_device,
    create_device_type,
    create_membership,
    create_user,
    create_workspace_with_owner,
)


@pytest.mark.asyncio
async def test_create_device_success(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    service = DeviceService()

    device = await service.create_device(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        device_type_id=device_type.id,
        device_uid="sensor-001",
        name="Temperature Sensor",
        manufacturer="Example",
        model="T-100",
        protocol=" MQTT ",
    )

    assert device.workspace_id == workspace.id
    assert device.device_type_id == device_type.id
    assert device.device_uid == "sensor-001"
    assert device.name == "Temperature Sensor"
    assert device.manufacturer == "Example"
    assert device.model == "T-100"
    assert device.protocol == "mqtt"
    assert device.lifecycle_status == "pending_provisioning"
    assert device.is_enabled is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_uid", "name"),
    [
        ("", "Valid Name"),
        ("   ", "Valid Name"),
        ("valid-uid", ""),
        ("valid-uid", "   "),
    ],
)
async def test_create_device_rejects_empty_identity(
    db_session, device_uid, name
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    service = DeviceService()

    with pytest.raises(DeviceInvalidInput):
        await service.create_device(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            device_type_id=device_type.id,
            device_uid=device_uid,
            name=name,
        )


@pytest.mark.asyncio
async def test_create_device_rejects_missing_device_type(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    service = DeviceService()

    with pytest.raises(DeviceTypeNotFound):
        await service.create_device(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            device_type_id=uuid4(),
            device_uid="sensor-missing-type",
            name="Sensor",
        )


@pytest.mark.asyncio
async def test_create_device_rejects_duplicate_uid_in_same_workspace(
    db_session,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    service = DeviceService()

    await service.create_device(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        device_type_id=device_type.id,
        device_uid="duplicate-device-uid",
        name="First Device",
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await service.create_device(
                db_session,
                actor_id=owner.id,
                workspace_id=workspace.id,
                device_type_id=device_type.id,
                device_uid="duplicate-device-uid",
                name="Second Device",
            )


@pytest.mark.asyncio
async def test_create_device_rejects_duplicate_uid_across_workspaces(
    db_session,
):
    workspace_a, owner_a, _ = await create_workspace_with_owner(db_session)
    workspace_b, owner_b, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    service = DeviceService()

    await service.create_device(
        db_session,
        actor_id=owner_a.id,
        workspace_id=workspace_a.id,
        device_type_id=device_type.id,
        device_uid="globally-duplicate-uid",
        name="Workspace A Device",
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await service.create_device(
                db_session,
                actor_id=owner_b.id,
                workspace_id=workspace_b.id,
                device_type_id=device_type.id,
                device_uid="globally-duplicate-uid",
                name="Workspace B Device",
            )


@pytest.mark.asyncio
async def test_list_devices_is_scoped_to_workspace(db_session):
    workspace_a, owner_a, _ = await create_workspace_with_owner(db_session)
    workspace_b, owner_b, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    device_a = await create_device(
        db_session,
        workspace=workspace_a,
        device_type=device_type,
        device_uid="workspace-a-device",
    )
    await create_device(
        db_session,
        workspace=workspace_b,
        device_type=device_type,
        device_uid="workspace-b-device",
    )

    service = DeviceService()
    devices = await service.list_devices(
        db_session,
        actor_id=owner_a.id,
        workspace_id=workspace_a.id,
    )

    assert [device.id for device in devices] == [device_a.id]

    devices_b = await service.list_devices(
        db_session,
        actor_id=owner_b.id,
        workspace_id=workspace_b.id,
    )
    assert len(devices_b) == 1
    assert devices_b[0].workspace_id == workspace_b.id


@pytest.mark.asyncio
async def test_get_device_rejects_cross_workspace_access(db_session):
    workspace_a, _, _ = await create_workspace_with_owner(db_session)
    workspace_b, owner_b, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    device_a = await create_device(
        db_session,
        workspace=workspace_a,
        device_type=device_type,
    )

    with pytest.raises(DeviceNotFound):
        await DeviceService().get_device(
            db_session,
            actor_id=owner_b.id,
            workspace_id=workspace_b.id,
            device_id=device_a.id,
        )


@pytest.mark.asyncio
async def test_update_device_success(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    device = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
        name="Old Name",
    )

    updated = await DeviceService().update_device(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        device_id=device.id,
        changes={
            "name": "  Updated Name  ",
            "manufacturer": "  Example Corp  ",
            "protocol": "  HTTP  ",
        },
    )

    assert updated.id == device.id
    assert updated.name == "Updated Name"
    assert updated.manufacturer == "Example Corp"
    assert updated.protocol == "http"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"unsupported_field": "value"},
        {"name": ""},
        {"name": "   "},
        {"protocol": ""},
        {"protocol": "   "},
    ],
)
async def test_update_device_rejects_invalid_changes(db_session, changes):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    device = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )

    with pytest.raises(DeviceInvalidInput):
        await DeviceService().update_device(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            device_id=device.id,
            changes=changes,
        )


@pytest.mark.asyncio
async def test_update_device_rejects_cross_workspace_access(db_session):
    workspace_a, _, _ = await create_workspace_with_owner(db_session)
    workspace_b, owner_b, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)
    device_a = await create_device(
        db_session,
        workspace=workspace_a,
        device_type=device_type,
    )

    with pytest.raises(DeviceNotFound):
        await DeviceService().update_device(
            db_session,
            actor_id=owner_b.id,
            workspace_id=workspace_b.id,
            device_id=device_a.id,
            changes={"name": "Unauthorized Update"},
        )


@pytest.mark.asyncio
async def test_viewer_cannot_create_or_update_device(db_session):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    viewer = await create_user(db_session)
    await create_membership(
        db_session,
        workspace=workspace,
        user=viewer,
        role="viewer",
    )
    device_type = await create_device_type(db_session)
    service = DeviceService()

    with pytest.raises(DevicePermissionDenied):
        await service.create_device(
            db_session,
            actor_id=viewer.id,
            workspace_id=workspace.id,
            device_type_id=device_type.id,
            device_uid="viewer-create-attempt",
            name="Viewer Device",
        )

    device = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )

    with pytest.raises(DevicePermissionDenied):
        await service.update_device(
            db_session,
            actor_id=viewer.id,
            workspace_id=workspace.id,
            device_id=device.id,
            changes={"name": "Viewer Update Attempt"},
        )
