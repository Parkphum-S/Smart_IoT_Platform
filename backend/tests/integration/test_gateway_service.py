"""Integration tests for gateway service operations."""

import pytest

from app.modules.devices.models import DeviceGateway
from app.modules.devices.services.exceptions import (
    GatewayCycleDetected,
    GatewayMembershipConflict,
    GatewayNotFound,
)
from app.modules.devices.services.gateway_service import GatewayService
from factories import (
    create_device,
    create_device_type,
    create_workspace_with_owner,
)


async def create_gateway(session, device):
    """Create a gateway record for an existing device."""
    gateway = DeviceGateway(
        device_id=device.id,
        workspace_id=device.workspace_id,
        gateway_type="generic",
        adapter_key="integration",
        configuration={},
    )
    session.add(gateway)
    await session.flush()
    return gateway


@pytest.mark.asyncio
async def test_assign_gateway_rejects_gateway_from_another_workspace(
    db_session,
):
    workspace_a, owner_a, _ = await create_workspace_with_owner(db_session)
    workspace_b, _, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    child = await create_device(
        db_session,
        workspace=workspace_a,
        device_type=device_type,
    )
    foreign_gateway = await create_device(
        db_session,
        workspace=workspace_b,
        device_type=device_type,
    )
    await create_gateway(db_session, foreign_gateway)

    service = GatewayService()

    with pytest.raises(GatewayNotFound):
        await service.assign_gateway(
            db_session,
            actor_id=owner_a.id,
            workspace_id=workspace_a.id,
            child_device_id=child.id,
            gateway_device_id=foreign_gateway.id,
        )


@pytest.mark.asyncio
async def test_assign_gateway_rejects_duplicate_primary_membership(
    db_session,
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    child = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )
    gateway_a = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )
    gateway_b = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )

    await create_gateway(db_session, gateway_a)
    await create_gateway(db_session, gateway_b)

    service = GatewayService()

    await service.assign_gateway(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        child_device_id=child.id,
        gateway_device_id=gateway_a.id,
    )

    with pytest.raises(GatewayMembershipConflict):
        await service.assign_gateway(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            child_device_id=child.id,
            gateway_device_id=gateway_b.id,
        )


@pytest.mark.asyncio
async def test_assign_gateway_rejects_cycle(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    device_a = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )
    device_b = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )

    await create_gateway(db_session, device_a)
    await create_gateway(db_session, device_b)

    service = GatewayService()

    # A -> B is valid.
    await service.assign_gateway(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        child_device_id=device_a.id,
        gateway_device_id=device_b.id,
    )

    # B -> A would create A -> B -> A.
    with pytest.raises(GatewayCycleDetected):
        await service.assign_gateway(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            child_device_id=device_b.id,
            gateway_device_id=device_a.id,
        )
