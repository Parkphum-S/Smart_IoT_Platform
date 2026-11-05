"""Integration tests for workspace creation and ownership invariants."""

import pytest
from sqlalchemy import func, select

from app.modules.monitoring.models import AuditLog
from app.modules.users.models import MembershipHistory, Workspace, WorkspaceMember
from app.modules.users.services.workspace_service import (
    WorkspaceCreatorNotActive,
    WorkspaceService,
)
from factories import create_user


@pytest.mark.asyncio
async def test_create_workspace_persists_owner_history_and_audit(db_session):
    creator = await create_user(db_session)
    service = WorkspaceService()

    workspace, membership = await service.create_workspace(
        db_session,
        creator_id=creator.id,
        name="Integration Workspace",
        description="Workspace lifecycle test",
        timezone="Asia/Bangkok",
    )

    assert workspace.id is not None
    assert membership.workspace_id == workspace.id
    assert membership.user_id == creator.id
    assert membership.role == "owner"
    assert membership.is_active is True

    history = (
        await db_session.execute(
            select(MembershipHistory).where(
                MembershipHistory.membership_id == membership.id
            )
        )
    ).scalar_one()

    assert history.event_type == "created"
    assert history.new_role == "owner"
    assert history.actor_id == creator.id
    assert history.subject_user_id == creator.id

    audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.workspace_id == workspace.id,
                AuditLog.action == "workspace.created",
            )
        )
    ).scalar_one()

    assert audit.actor_id == creator.id
    assert audit.resource_id == workspace.id
    assert audit.details["owner_user_id"] == str(creator.id)


@pytest.mark.asyncio
async def test_workspace_creation_rejects_inactive_creator(db_session):
    creator = await create_user(db_session, is_active=False)
    service = WorkspaceService()

    with pytest.raises(WorkspaceCreatorNotActive):
        await service.create_workspace(
            db_session,
            creator_id=creator.id,
            name="Should Not Exist",
            description=None,
            timezone="UTC",
        )

    count = await db_session.scalar(
        select(func.count()).select_from(Workspace)
    )
    assert count == 0


@pytest.mark.asyncio
async def test_workspace_has_exactly_one_active_owner(db_session):
    """Verify the database prevents a second active owner."""
    from sqlalchemy.exc import IntegrityError

    from factories import create_workspace_with_owner

    workspace, owner, owner_membership = await create_workspace_with_owner(
        db_session
    )
    second_user = await create_user(db_session)

    async with db_session.begin_nested():
        db_session.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=second_user.id,
                role="owner",
                is_active=True,
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    assert owner_membership.role == "owner"
    assert owner.is_active is True
