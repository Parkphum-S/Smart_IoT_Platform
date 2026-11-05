"""Integration tests for membership lifecycle and permanent records."""

import pytest
from sqlalchemy import select

from app.modules.monitoring.models import AuditLog
from app.modules.users.models import MembershipHistory, WorkspaceMember
from app.modules.users.services.membership.membership_service import (
    MembershipService,
)
from factories import create_user, create_workspace_with_owner


@pytest.mark.asyncio
async def test_membership_add_change_deactivate_reactivate(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    target = await create_user(db_session)
    service = MembershipService()

    membership = await service.add_member(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        user_id=target.id,
        role="viewer",
    )

    assert membership.role == "viewer"
    assert membership.is_active is True

    await service.change_role(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        membership_id=membership.id,
        new_role="operator",
    )

    assert membership.role == "operator"

    await service.deactivate_member(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        membership_id=membership.id,
    )

    assert membership.is_active is False

    await service.reactivate_member(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        membership_id=membership.id,
    )

    assert membership.is_active is True
    assert membership.role == "operator"

    history = (
        await db_session.execute(
            select(MembershipHistory)
            .where(MembershipHistory.membership_id == membership.id)
            .order_by(MembershipHistory.event_sequence)
        )
    ).scalars().all()

    assert [event.event_type for event in history] == [
        "created",
        "role_changed",
        "deactivated",
        "reactivated",
    ]

    assert history[0].new_role == "viewer"
    assert history[1].previous_role == "viewer"
    assert history[1].new_role == "operator"
    assert history[2].previous_role == "operator"
    assert history[3].new_role == "operator"

    audit_actions = (
        await db_session.execute(
            select(AuditLog.action)
            .where(AuditLog.workspace_id == workspace.id)
            .order_by(AuditLog.created_at, AuditLog.id)
        )
    ).scalars().all()

    assert audit_actions.count("membership.created") == 1
    assert audit_actions.count("membership.role_changed") == 1
    assert audit_actions.count("membership.deactivated") == 1
    assert audit_actions.count("membership.reactivated") == 1


@pytest.mark.asyncio
async def test_ownership_transfer_updates_both_members_and_history(db_session):
    workspace, old_owner, old_membership = await create_workspace_with_owner(
        db_session
    )
    target = await create_user(db_session)

    service = MembershipService()

    target_membership = await service.add_member(
        db_session,
        actor_id=old_owner.id,
        workspace_id=workspace.id,
        user_id=target.id,
        role="operator",
    )

    old_result, new_result = await service.transfer_ownership(
        db_session,
        actor_id=old_owner.id,
        workspace_id=workspace.id,
        target_membership_id=target_membership.id,
    )

    assert old_result.role == "admin"
    assert new_result.role == "owner"

    active_owners = (
        await db_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.role == "owner",
                WorkspaceMember.is_active.is_(True),
            )
        )
    ).scalars().all()

    assert len(active_owners) == 1
    assert active_owners[0].user_id == target.id

    old_history = (
        await db_session.execute(
            select(MembershipHistory)
            .where(
                MembershipHistory.membership_id == old_membership.id,
                MembershipHistory.event_type == "ownership_transferred",
            )
        )
    ).scalar_one()

    new_history = (
        await db_session.execute(
            select(MembershipHistory)
            .where(
                MembershipHistory.membership_id == target_membership.id,
                MembershipHistory.event_type == "ownership_transferred",
            )
        )
    ).scalar_one()

    assert old_history.previous_role == "owner"
    assert old_history.new_role == "admin"
    assert new_history.previous_role == "operator"
    assert new_history.new_role == "owner"

    audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.workspace_id == workspace.id,
                AuditLog.action == "ownership.transferred",
            )
        )
    ).scalar_one()

    assert audit.details["previous_owner_user_id"] == str(old_owner.id)
    assert audit.details["new_owner_user_id"] == str(target.id)
