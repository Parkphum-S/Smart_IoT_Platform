from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.users.services.membership.exceptions import (
    DeactivationHistoryNotFound,
    InvalidRoleAssignment,
    InvalidOwnershipTransferTarget,
    MembershipAlreadyActive,
    MembershipAlreadyExists,
    MembershipInactive,
    OwnerDeactivationProhibited,
    SelfManagementProhibited,
    UserNotFoundOrInactive,
)
from app.modules.users.services.membership.membership_service import (
    MembershipService,
)


@pytest.mark.parametrize(
    ("actor_role", "target_role", "expected"),
    [
        ("owner", "admin", "admin"),
        ("owner", "operator", "operator"),
        ("owner", "viewer", "viewer"),
        ("admin", "operator", "operator"),
        ("admin", "viewer", "viewer"),
    ],
)
def test_validate_allowed_role_assignments(actor_role, target_role, expected):
    assert MembershipService._validate_role_assignment(
        actor_role=actor_role,
        target_role=target_role,
    ) == expected


@pytest.mark.parametrize(
    ("actor_role", "target_role"),
    [
        ("owner", "owner"),
        ("admin", "owner"),
        ("admin", "admin"),
        ("operator", "viewer"),
        ("viewer", "operator"),
        ("unknown", "viewer"),
        ("owner", "unknown"),
    ],
)
def test_validate_rejects_disallowed_role_assignments(actor_role, target_role):
    with pytest.raises(InvalidRoleAssignment):
        MembershipService._validate_role_assignment(
            actor_role=actor_role,
            target_role=target_role,
        )


@pytest.mark.asyncio
async def test_add_member_creates_membership_and_records_history_and_audit():
    service = MembershipService()
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_active_user=AsyncMock(return_value=object()),
        get_membership_by_user=AsyncMock(return_value=None),
        create_membership=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid4(),
                user_id=uuid4(),
                role="operator",
                is_active=True,
            )
        ),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    actor_id = uuid4()
    user_id = uuid4()
    workspace_id = uuid4()
    membership = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        role="operator",
        is_active=True,
    )
    service.repository.create_membership.return_value = membership

    result = await service.add_member(
        AsyncMock(),
        actor_id=actor_id,
        workspace_id=workspace_id,
        user_id=user_id,
        role="operator",
    )

    assert result is membership
    service.repository.create_membership.assert_awaited_once_with(
        service.repository.create_membership.await_args.args[0],
        workspace_id=workspace_id,
        user_id=user_id,
        role="operator",
    )
    service.repository.add_membership_history.assert_awaited_once()
    history_kwargs = service.repository.add_membership_history.await_args.kwargs
    assert history_kwargs["event_type"] == "created"
    assert history_kwargs["new_role"] == "operator"
    service.repository.add_audit_log.assert_awaited_once()
    audit_kwargs = service.repository.add_audit_log.await_args.kwargs
    assert audit_kwargs["action"] == "membership.created"


@pytest.mark.asyncio
async def test_add_member_rejects_existing_inactive_membership():
    service = MembershipService()
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_active_user=AsyncMock(return_value=object()),
        get_membership_by_user=AsyncMock(
            return_value=SimpleNamespace(is_active=False)
        ),
        create_membership=AsyncMock(),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(MembershipAlreadyExists):
        await service.add_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            user_id=uuid4(),
            role="viewer",
        )

    service.repository.create_membership.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_member_rejects_inactive_platform_user():
    service = MembershipService()
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_active_user=AsyncMock(return_value=None),
        get_membership_by_user=AsyncMock(),
        create_membership=AsyncMock(),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(UserNotFoundOrInactive):
        await service.add_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            user_id=uuid4(),
            role="viewer",
        )

    service.repository.get_membership_by_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_member_rejects_self_management():
    service = MembershipService()
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_active_user=AsyncMock(),
        get_membership_by_user=AsyncMock(),
        create_membership=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    actor_id = uuid4()

    with pytest.raises(SelfManagementProhibited):
        await service.add_member(
            AsyncMock(),
            actor_id=actor_id,
            workspace_id=uuid4(),
            user_id=actor_id,
            role="viewer",
        )

    service.repository.get_active_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_role_updates_membership_and_records_history_and_audit():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        role="viewer",
        is_active=True,
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )
    session = SimpleNamespace(flush=AsyncMock())

    actor_id = uuid4()
    workspace_id = uuid4()

    result = await service.change_role(
        session,
        actor_id=actor_id,
        workspace_id=workspace_id,
        membership_id=membership.id,
        new_role="operator",
    )

    assert result is membership
    assert membership.role == "operator"
    session.flush.assert_awaited_once()

    history_kwargs = service.repository.add_membership_history.await_args.kwargs
    assert history_kwargs["event_type"] == "role_changed"
    assert history_kwargs["previous_role"] == "viewer"
    assert history_kwargs["new_role"] == "operator"

    audit_kwargs = service.repository.add_audit_log.await_args.kwargs
    assert audit_kwargs["action"] == "membership.role_changed"


@pytest.mark.asyncio
async def test_change_role_rejects_inactive_membership():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        role="viewer",
        is_active=False,
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(MembershipInactive):
        await service.change_role(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
            new_role="operator",
        )

    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_role_rejects_self_management():
    service = MembershipService()
    actor_id = uuid4()
    membership = SimpleNamespace(
        id=uuid4(),
        user_id=actor_id,
        role="owner",
        is_active=True,
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(SelfManagementProhibited):
        await service.change_role(
            AsyncMock(),
            actor_id=actor_id,
            workspace_id=uuid4(),
            membership_id=membership.id,
            new_role="viewer",
        )

    service.repository.add_membership_history.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_cannot_change_another_admin_role():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        role="admin",
        is_active=True,
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="admin"))
    )

    with pytest.raises(InvalidRoleAssignment):
        await service.change_role(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
            new_role="viewer",
        )

    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()


@pytest.mark.asyncio
async def test_deactivate_member_records_history_and_audit():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="operator", is_active=True
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )
    session = SimpleNamespace(flush=AsyncMock())

    result = await service.deactivate_member(
        session,
        actor_id=uuid4(),
        workspace_id=uuid4(),
        membership_id=membership.id,
    )

    assert result is membership
    assert membership.is_active is False
    assert membership.role == "operator"
    assert service.repository.add_membership_history.await_args.kwargs == {
        "workspace_id": service.repository.add_membership_history.await_args.kwargs["workspace_id"],
        "membership_id": membership.id,
        "actor_id": service.repository.add_membership_history.await_args.kwargs["actor_id"],
        "subject_user_id": membership.user_id,
        "event_type": "deactivated",
        "previous_role": "operator",
    }
    assert service.repository.add_audit_log.await_args.kwargs["action"] == "membership.deactivated"


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_another_admin():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="admin", is_active=True
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="admin"))
    )

    with pytest.raises(InvalidRoleAssignment):
        await service.deactivate_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
        )

    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()


@pytest.mark.asyncio
async def test_owner_cannot_be_deactivated():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="owner", is_active=True
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(OwnerDeactivationProhibited):
        await service.deactivate_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
        )


@pytest.mark.asyncio
async def test_reactivate_member_restores_role_from_latest_deactivation():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="operator", is_active=False
    )
    deactivation = SimpleNamespace(previous_role="admin")
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        get_latest_deactivation=AsyncMock(return_value=deactivation),
        get_active_user=AsyncMock(return_value=object()),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )
    session = SimpleNamespace(flush=AsyncMock())

    result = await service.reactivate_member(
        session,
        actor_id=uuid4(),
        workspace_id=uuid4(),
        membership_id=membership.id,
    )

    assert result is membership
    assert membership.is_active is True
    assert membership.role == "admin"
    history = service.repository.add_membership_history.await_args.kwargs
    assert history["event_type"] == "reactivated"
    assert history["previous_role"] == "operator"
    assert history["new_role"] == "admin"
    assert service.repository.add_audit_log.await_args.kwargs["action"] == "membership.reactivated"


@pytest.mark.asyncio
async def test_admin_cannot_reactivate_membership_with_admin_role():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="admin", is_active=False
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        get_active_user=AsyncMock(return_value=object()),
        get_latest_deactivation=AsyncMock(
            return_value=SimpleNamespace(previous_role="admin")
        ),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="admin"))
    )

    with pytest.raises(InvalidRoleAssignment):
        await service.reactivate_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
        )

    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()


@pytest.mark.asyncio
async def test_reactivate_member_requires_deactivation_history():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="viewer", is_active=False
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        get_active_user=AsyncMock(return_value=object()),
        get_latest_deactivation=AsyncMock(return_value=None),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(DeactivationHistoryNotFound):
        await service.reactivate_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
        )

@pytest.mark.asyncio
async def test_transfer_ownership_updates_both_members_and_records_history():
    service = MembershipService()
    actor_id = uuid4()
    workspace_id = uuid4()
    old_owner = SimpleNamespace(
        id=uuid4(), user_id=actor_id, role="owner", is_active=True
    )
    new_owner = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="operator", is_active=True
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(
            side_effect=[old_owner, new_owner]
        ),
        get_active_user=AsyncMock(return_value=object()),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=old_owner)
    )
    session = SimpleNamespace(flush=AsyncMock())

    result = await service.transfer_ownership(
        session,
        actor_id=actor_id,
        workspace_id=workspace_id,
        target_membership_id=new_owner.id,
    )

    assert result == (old_owner, new_owner)
    assert old_owner.role == "admin"
    assert new_owner.role == "owner"
    assert old_owner.is_active is True
    assert new_owner.is_active is True
    assert session.flush.await_count == 2

    history_calls = service.repository.add_membership_history.await_args_list
    assert len(history_calls) == 2
    assert history_calls[0].kwargs["event_type"] == "ownership_transferred"
    assert history_calls[0].kwargs["previous_role"] == "owner"
    assert history_calls[0].kwargs["new_role"] == "admin"
    assert history_calls[1].kwargs["event_type"] == "ownership_transferred"
    assert history_calls[1].kwargs["previous_role"] == "operator"
    assert history_calls[1].kwargs["new_role"] == "owner"

    audit = service.repository.add_audit_log.await_args.kwargs
    assert audit["action"] == "ownership.transferred"
    assert audit["resource_id"] == workspace_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target_role", "target_active"),
    [
        ("owner", True),
        ("admin", False),
    ],
)
async def test_transfer_ownership_rejects_ineligible_target(
    target_role, target_active
):
    service = MembershipService()
    actor_id = uuid4()
    old_owner = SimpleNamespace(
        id=uuid4(), user_id=actor_id, role="owner", is_active=True
    )
    new_owner = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        role=target_role,
        is_active=target_active,
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(
            side_effect=[old_owner, new_owner]
        ),
        get_active_user=AsyncMock(return_value=object()),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=old_owner)
    )

    with pytest.raises(InvalidOwnershipTransferTarget):
        await service.transfer_ownership(
            AsyncMock(),
            actor_id=actor_id,
            workspace_id=uuid4(),
            target_membership_id=new_owner.id,
        )

    service.repository.get_active_user.assert_not_awaited()
    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()


@pytest.mark.asyncio
async def test_transfer_ownership_rejects_inactive_platform_user():
    service = MembershipService()
    actor_id = uuid4()
    old_owner = SimpleNamespace(
        id=uuid4(), user_id=actor_id, role="owner", is_active=True
    )
    new_owner = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="viewer", is_active=True
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(
            side_effect=[old_owner, new_owner]
        ),
        get_active_user=AsyncMock(return_value=None),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=old_owner)
    )

    with pytest.raises(InvalidOwnershipTransferTarget):
        await service.transfer_ownership(
            AsyncMock(),
            actor_id=actor_id,
            workspace_id=uuid4(),
            target_membership_id=new_owner.id,
        )

    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()



@pytest.mark.asyncio
async def test_reactivate_member_rejects_inactive_platform_user():
    service = MembershipService()
    membership = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), role="viewer", is_active=False
    )
    service.repository = SimpleNamespace(
        get_workspace_for_update=AsyncMock(return_value=object()),
        get_membership_for_update=AsyncMock(return_value=membership),
        get_active_user=AsyncMock(return_value=None),
        get_latest_deactivation=AsyncMock(),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner"))
    )

    with pytest.raises(UserNotFoundOrInactive):
        await service.reactivate_member(
            AsyncMock(),
            actor_id=uuid4(),
            workspace_id=uuid4(),
            membership_id=membership.id,
        )

    assert membership.is_active is False
    service.repository.get_latest_deactivation.assert_not_awaited()
    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()
