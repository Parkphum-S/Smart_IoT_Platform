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


@pytest.mark.asyncio
async def test_update_gateway_rejects_gateway_from_another_workspace(
    db_session,
):
    workspace_a, owner_a, _ = await create_workspace_with_owner(db_session)
    workspace_b, _, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    foreign_device = await create_device(
        db_session,
        workspace=workspace_b,
        device_type=device_type,
    )
    await create_gateway(db_session, foreign_device)

    service = GatewayService()

    with pytest.raises(GatewayNotFound):
        await service.update_gateway(
            db_session,
            actor_id=owner_a.id,
            workspace_id=workspace_a.id,
            device_id=foreign_device.id,
            gateway_type="modified",
        )


@pytest.mark.asyncio
async def test_remove_gateway_rejects_missing_membership(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    device_type = await create_device_type(db_session)

    child = await create_device(
        db_session,
        workspace=workspace,
        device_type=device_type,
    )

    service = GatewayService()

    with pytest.raises(GatewayMembershipConflict):
        await service.remove_gateway(
            db_session,
            actor_id=owner.id,
            workspace_id=workspace.id,
            child_device_id=child.id,
        )

# PostgreSQL concurrency tests use independent sessions and committed fixtures.


async def _assert_workspace_lock_blocks(factory, workspace_id, task):
    import asyncio

    done, _ = await asyncio.wait({task}, timeout=0.15)
    assert not done, "Competing operation should wait for the workspace lock."

    from sqlalchemy import func, select

    async with factory() as probe:
        lock_available = await probe.scalar(
            select(
                func.pg_try_advisory_xact_lock(
                    func.hashtextextended(str(workspace_id), 0)
                )
            )
        )

    assert lock_available is False


@pytest.mark.asyncio
async def test_concurrent_gateway_assignments_serialize(
    gateway_secret_concurrency_context,
):
    import asyncio

    from app.modules.devices.models import DeviceGatewayMember

    context = gateway_secret_concurrency_context
    factory = context["session_factory"]
    workspace_id = context["workspace_id"]
    owner_id = context["owner_id"]
    child_id = context["child_device_id"]
    gateway_a = context["gateway_device_id"]
    gateway_b = context["second_gateway_device_id"]
    service = GatewayService()

    first_session = factory()
    first_transaction = await first_session.begin()
    second_task = None

    try:
        await service.assign_gateway(
            first_session,
            actor_id=owner_id,
            workspace_id=workspace_id,
            child_device_id=child_id,
            gateway_device_id=gateway_a,
        )

        second_started = asyncio.Event()

        async def competing_assign():
            async with factory() as session:
                async with session.begin():
                    second_started.set()
                    return await service.assign_gateway(
                        session,
                        actor_id=owner_id,
                        workspace_id=workspace_id,
                        child_device_id=child_id,
                        gateway_device_id=gateway_b,
                    )

        second_task = asyncio.create_task(competing_assign())
        await asyncio.wait_for(second_started.wait(), timeout=5)
        await _assert_workspace_lock_blocks(
            factory, workspace_id, second_task
        )

        await first_transaction.commit()

        with pytest.raises(GatewayMembershipConflict):
            await asyncio.wait_for(second_task, timeout=5)

        async with factory() as verify:
            membership = await verify.get(
                DeviceGatewayMember, child_id
            )
            assert membership is not None
            assert membership.gateway_device_id == gateway_a

    finally:
        if second_task is not None and not second_task.done():
            second_task.cancel()
            await asyncio.gather(second_task, return_exceptions=True)
        if first_transaction.is_active:
            await first_transaction.rollback()
        await first_session.close()


@pytest.mark.asyncio
async def test_concurrent_gateway_assignments_prevent_cycle(
    gateway_secret_concurrency_context,
):
    import asyncio

    context = gateway_secret_concurrency_context
    factory = context["session_factory"]
    workspace_id = context["workspace_id"]
    owner_id = context["owner_id"]
    gateway_a = context["gateway_device_id"]
    gateway_b = context["second_gateway_device_id"]
    service = GatewayService()

    first_session = factory()
    first_transaction = await first_session.begin()
    second_task = None

    try:
        await service.assign_gateway(
            first_session,
            actor_id=owner_id,
            workspace_id=workspace_id,
            child_device_id=gateway_a,
            gateway_device_id=gateway_b,
        )

        second_started = asyncio.Event()

        async def competing_assign():
            async with factory() as session:
                async with session.begin():
                    second_started.set()
                    return await service.assign_gateway(
                        session,
                        actor_id=owner_id,
                        workspace_id=workspace_id,
                        child_device_id=gateway_b,
                        gateway_device_id=gateway_a,
                    )

        second_task = asyncio.create_task(competing_assign())
        await asyncio.wait_for(second_started.wait(), timeout=5)
        await _assert_workspace_lock_blocks(
            factory, workspace_id, second_task
        )

        await first_transaction.commit()

        with pytest.raises(GatewayCycleDetected):
            await asyncio.wait_for(second_task, timeout=5)

    finally:
        if second_task is not None and not second_task.done():
            second_task.cancel()
            await asyncio.gather(second_task, return_exceptions=True)
        if first_transaction.is_active:
            await first_transaction.rollback()
        await first_session.close()


@pytest.mark.asyncio
async def test_concurrent_gateway_update_and_membership_remove_serialize(
    gateway_secret_concurrency_context,
):
    import asyncio

    from app.modules.devices.models import DeviceGatewayMember

    context = gateway_secret_concurrency_context
    factory = context["session_factory"]
    workspace_id = context["workspace_id"]
    owner_id = context["owner_id"]
    child_id = context["child_device_id"]
    gateway_id = context["gateway_device_id"]
    service = GatewayService()

    async with factory() as setup:
        async with setup.begin():
            await service.assign_gateway(
                setup,
                actor_id=owner_id,
                workspace_id=workspace_id,
                child_device_id=child_id,
                gateway_device_id=gateway_id,
            )

    first_session = factory()
    first_transaction = await first_session.begin()
    second_task = None

    try:
        await service.update_gateway(
            first_session,
            actor_id=owner_id,
            workspace_id=workspace_id,
            device_id=gateway_id,
            adapter_key="concurrency-updated",
        )

        second_started = asyncio.Event()

        async def competing_remove():
            async with factory() as session:
                async with session.begin():
                    second_started.set()
                    await service.remove_gateway(
                        session,
                        actor_id=owner_id,
                        workspace_id=workspace_id,
                        child_device_id=child_id,
                    )

        second_task = asyncio.create_task(competing_remove())
        await asyncio.wait_for(second_started.wait(), timeout=5)
        await _assert_workspace_lock_blocks(
            factory, workspace_id, second_task
        )

        await first_transaction.commit()
        await asyncio.wait_for(second_task, timeout=5)

        async with factory() as verify:
            membership = await verify.get(
                DeviceGatewayMember, child_id
            )
            from app.modules.devices.models import DeviceGateway

            gateway = await verify.get(DeviceGateway, gateway_id)

            assert membership is None
            assert gateway is not None
            assert gateway.adapter_key == "concurrency-updated"

    finally:
        if second_task is not None and not second_task.done():
            second_task.cancel()
            await asyncio.gather(second_task, return_exceptions=True)
        if first_transaction.is_active:
            await first_transaction.rollback()
        await first_session.close()
