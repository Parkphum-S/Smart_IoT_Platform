"""Integration tests for workspace read and update permissions."""

import pytest
from sqlalchemy import func, select

from app.modules.monitoring.models import AuditLog
from app.modules.users.services.workspace_service import (
    WorkspaceNotFound,
    WorkspacePermissionDenied,
    WorkspaceService,
)
from factories import (
    create_membership,
    create_user,
    create_workspace_with_owner,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["owner", "admin", "operator", "viewer"])
async def test_workspace_read_all_active_member_roles(db_session, role):
    workspace, owner, _ = await create_workspace_with_owner(
        db_session,
        workspace_name="Integration Workspace",
    )

    if role == "owner":
        actor = owner
    else:
        actor = await create_user(db_session)
        await create_membership(
            db_session,
            workspace=workspace,
            user=actor,
            role=role,
        )

    result = await WorkspaceService().get_workspace(
        db_session,
        actor_id=actor.id,
        workspace_id=workspace.id,
    )

    assert result.id == workspace.id
    assert result.name == workspace.name
    assert result.description == workspace.description
    assert result.timezone == workspace.timezone


@pytest.mark.asyncio
async def test_workspace_read_rejects_non_member(db_session):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    outsider = await create_user(db_session)

    with pytest.raises(WorkspacePermissionDenied):
        await WorkspaceService().get_workspace(
            db_session,
            actor_id=outsider.id,
            workspace_id=workspace.id,
        )


@pytest.mark.asyncio
async def test_workspace_read_rejects_inactive_membership(db_session):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    actor = await create_user(db_session)
    await create_membership(
        db_session,
        workspace=workspace,
        user=actor,
        role="viewer",
        is_active=False,
    )

    with pytest.raises(WorkspacePermissionDenied):
        await WorkspaceService().get_workspace(
            db_session,
            actor_id=actor.id,
            workspace_id=workspace.id,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["owner", "admin"])
async def test_workspace_update_persists_fields_and_audit(db_session, role):
    workspace, owner, _ = await create_workspace_with_owner(
        db_session,
        workspace_name="Integration Workspace",
    )

    if role == "owner":
        actor = owner
    else:
        actor = await create_user(db_session)
        await create_membership(
            db_session,
            workspace=workspace,
            user=actor,
            role=role,
        )

    result = await WorkspaceService().update_workspace(
        db_session,
        actor_id=actor.id,
        workspace_id=workspace.id,
        changes={
            "name": "Updated Integration Workspace",
            "description": "Updated through WorkspaceService",
            "timezone": "Asia/Bangkok",
        },
    )

    assert result.name == "Updated Integration Workspace"
    assert result.description == "Updated through WorkspaceService"
    assert result.timezone == "Asia/Bangkok"

    await db_session.flush()
    await db_session.refresh(workspace)

    assert workspace.name == "Updated Integration Workspace"
    assert workspace.description == "Updated through WorkspaceService"
    assert workspace.timezone == "Asia/Bangkok"

    audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.workspace_id == workspace.id,
                AuditLog.action == "workspace.updated",
            )
        )
    ).scalar_one()

    assert audit.actor_id == actor.id
    assert audit.resource_type == "workspace"
    assert audit.resource_id == workspace.id
    assert audit.details == {
        "changed_fields": {
            "name": {
                "old": "Integration Workspace",
                "new": "Updated Integration Workspace",
            },
            "description": {
                "old": None,
                "new": "Updated through WorkspaceService",
            },
            "timezone": {
                "old": "UTC",
                "new": "Asia/Bangkok",
            },
        }
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["operator", "viewer"])
async def test_workspace_update_rejects_read_only_roles(db_session, role):
    workspace, _, _ = await create_workspace_with_owner(
        db_session,
        workspace_name="Original Workspace",
    )
    actor = await create_user(db_session)
    await create_membership(
        db_session,
        workspace=workspace,
        user=actor,
        role=role,
    )

    with pytest.raises(WorkspacePermissionDenied):
        await WorkspaceService().update_workspace(
            db_session,
            actor_id=actor.id,
            workspace_id=workspace.id,
            changes={"name": "Unauthorized Change"},
        )

    await db_session.refresh(workspace)
    assert workspace.name == "Original Workspace"

    audit_count = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.workspace_id == workspace.id,
            AuditLog.action == "workspace.updated",
        )
    )
    assert audit_count == 0


@pytest.mark.asyncio
async def test_workspace_update_rejects_non_member(db_session):
    workspace, _, _ = await create_workspace_with_owner(
        db_session,
        workspace_name="Integration Workspace",
    )
    outsider = await create_user(db_session)

    with pytest.raises(WorkspacePermissionDenied):
        await WorkspaceService().update_workspace(
            db_session,
            actor_id=outsider.id,
            workspace_id=workspace.id,
            changes={"name": "Unauthorized Change"},
        )

    await db_session.refresh(workspace)
    assert workspace.name == "Integration Workspace"

    audit_count = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.workspace_id == workspace.id,
            AuditLog.action == "workspace.updated",
        )
    )
    assert audit_count == 0


@pytest.mark.asyncio
async def test_workspace_update_with_same_values_does_not_create_audit(db_session):
    workspace, owner, _ = await create_workspace_with_owner(
        db_session,
        workspace_name="Unchanged Workspace",
    )
    workspace.description = "Existing description"
    workspace.timezone = "Asia/Bangkok"
    await db_session.flush()

    result = await WorkspaceService().update_workspace(
        db_session,
        actor_id=owner.id,
        workspace_id=workspace.id,
        changes={
            "name": "Unchanged Workspace",
            "description": "Existing description",
            "timezone": "Asia/Bangkok",
        },
    )

    assert result.name == "Unchanged Workspace"

    audit_count = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.workspace_id == workspace.id,
            AuditLog.action == "workspace.updated",
        )
    )
    assert audit_count == 0


@pytest.mark.asyncio
async def test_workspace_read_returns_not_found_for_missing_workspace(db_session):
    from uuid import uuid4

    actor = await create_user(db_session)

    with pytest.raises(WorkspaceNotFound):
        await WorkspaceService().get_workspace(
            db_session,
            actor_id=actor.id,
            workspace_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_workspace_update_returns_not_found_for_missing_workspace(db_session):
    from uuid import uuid4

    actor = await create_user(db_session)

    with pytest.raises(WorkspaceNotFound):
        await WorkspaceService().update_workspace(
            db_session,
            actor_id=actor.id,
            workspace_id=uuid4(),
            changes={"name": "Missing Workspace"},
        )
