from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.users.services import workspace_service as service_module
from app.modules.users.services.workspace_service import (
    WorkspaceCreatorNotActive,
    WorkspaceService,
)


@pytest.mark.asyncio
async def test_create_workspace_creates_owner_history_and_audit(monkeypatch):
    creator_id = uuid4()
    workspace_id = uuid4()
    membership_id = uuid4()

    creator = SimpleNamespace(id=creator_id)
    membership = SimpleNamespace(
        id=membership_id,
        role="owner",
        is_active=True,
    )

    class WorkspaceStub:
        def __new__(cls, **kwargs):
            return SimpleNamespace(id=workspace_id, **kwargs)

    monkeypatch.setattr(service_module, "Workspace", WorkspaceStub)

    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_active_user=AsyncMock(return_value=creator),
        create_membership=AsyncMock(return_value=membership),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )

    session = SimpleNamespace(
        add=MagicMock(),
        flush=AsyncMock(),
    )

    result_workspace, result_membership = await service.create_workspace(
        session,
        creator_id=creator_id,
        name="Test Workspace",
        description="Test description",
        timezone="Asia/Bangkok",
    )

    assert result_workspace.id == workspace_id
    assert result_workspace.name == "Test Workspace"
    assert result_membership is membership
    session.add.assert_called_once_with(result_workspace)
    session.flush.assert_awaited_once()

    service.repository.get_active_user.assert_awaited_once_with(
        session,
        user_id=creator_id,
    )
    service.repository.create_membership.assert_awaited_once_with(
        session,
        workspace_id=workspace_id,
        user_id=creator_id,
        role="owner",
    )

    history = service.repository.add_membership_history.await_args.kwargs
    assert history["event_type"] == "created"
    assert history["new_role"] == "owner"
    assert history["actor_id"] == creator_id
    assert history["subject_user_id"] == creator_id

    audit = service.repository.add_audit_log.await_args.kwargs
    assert audit["action"] == "workspace.created"
    assert audit["resource_type"] == "workspace"
    assert audit["resource_id"] == workspace_id
    assert audit["actor_id"] == creator_id


@pytest.mark.asyncio
async def test_create_workspace_rejects_inactive_creator():
    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_active_user=AsyncMock(return_value=None),
        create_membership=AsyncMock(),
        add_membership_history=AsyncMock(),
        add_audit_log=AsyncMock(),
    )
    session = SimpleNamespace(add=MagicMock(), flush=AsyncMock())

    with pytest.raises(WorkspaceCreatorNotActive):
        await service.create_workspace(
            session,
            creator_id=uuid4(),
            name="Test Workspace",
            description=None,
            timezone="UTC",
        )

    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    service.repository.create_membership.assert_not_awaited()
    service.repository.add_membership_history.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_workspace_records_audit_for_changed_fields():
    from app.modules.users.services.authorization.permissions import Permission

    actor_id = uuid4()
    workspace_id = uuid4()
    workspace = SimpleNamespace(
        id=workspace_id,
        name="Old name",
        description="Old description",
        timezone="UTC",
    )

    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_workspace=AsyncMock(return_value=workspace),
        get_workspace_for_update=AsyncMock(return_value=workspace),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner")),
    )
    session = SimpleNamespace(flush=AsyncMock())

    result = await service.update_workspace(
        session,
        actor_id=actor_id,
        workspace_id=workspace_id,
        changes={
            "name": "New name",
            "description": None,
        },
    )

    assert result.name == "New name"
    assert result.description is None
    assert result.timezone == "UTC"

    assert service.authorization.authorize.await_count == 2
    service.authorization.authorize.assert_awaited_with(
        session,
        user_id=actor_id,
        workspace_id=workspace_id,
        permission=Permission.WORKSPACE_UPDATE,
    )

    audit = service.repository.add_audit_log.await_args.kwargs
    assert audit["action"] == "workspace.updated"
    assert audit["resource_id"] == workspace_id
    assert audit["details"]["changed_fields"] == {
        "name": {"old": "Old name", "new": "New name"},
        "description": {"old": "Old description", "new": None},
    }
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_workspace_does_not_audit_when_values_are_unchanged():
    workspace_id = uuid4()
    actor_id = uuid4()
    workspace = SimpleNamespace(
        id=workspace_id,
        name="Same name",
        description=None,
        timezone="UTC",
    )

    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_workspace=AsyncMock(return_value=workspace),
        get_workspace_for_update=AsyncMock(return_value=workspace),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner")),
    )
    session = SimpleNamespace(flush=AsyncMock())

    await service.update_workspace(
        session,
        actor_id=actor_id,
        workspace_id=workspace_id,
        changes={"name": "Same name"},
    )

    service.repository.add_audit_log.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_workspace_rejects_actor_without_update_permission():
    from app.modules.users.services.authorization.authorization_service import (
        PermissionDenied,
    )
    from app.modules.users.services.workspace_service import (
        WorkspacePermissionDenied,
    )

    workspace = SimpleNamespace(
        id=uuid4(),
        name="Existing",
        description=None,
        timezone="UTC",
    )
    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_workspace=AsyncMock(return_value=workspace),
        get_workspace_for_update=AsyncMock(return_value=workspace),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(side_effect=PermissionDenied),
    )
    session = SimpleNamespace(flush=AsyncMock())

    with pytest.raises(WorkspacePermissionDenied):
        await service.update_workspace(
            session,
            actor_id=uuid4(),
            workspace_id=workspace.id,
            changes={"name": "Unauthorized"},
        )

    service.repository.get_workspace_for_update.assert_not_awaited()
    service.repository.add_audit_log.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_workspace_rechecks_permission_after_lock():
    from app.modules.users.services.authorization.authorization_service import (
        PermissionDenied,
    )
    from app.modules.users.services.workspace_service import (
        WorkspacePermissionDenied,
    )

    actor_id = uuid4()
    workspace = SimpleNamespace(
        id=uuid4(),
        name="Existing",
        description=None,
        timezone="UTC",
    )

    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_workspace=AsyncMock(return_value=workspace),
        get_workspace_for_update=AsyncMock(return_value=workspace),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(
            side_effect=[
                SimpleNamespace(role="owner"),
                PermissionDenied,
            ]
        ),
    )
    session = SimpleNamespace(flush=AsyncMock())

    with pytest.raises(WorkspacePermissionDenied):
        await service.update_workspace(
            session,
            actor_id=actor_id,
            workspace_id=workspace.id,
            changes={"name": "Must not be saved"},
        )

    assert service.authorization.authorize.await_count == 2
    service.repository.get_workspace_for_update.assert_awaited_once()
    service.repository.add_audit_log.assert_not_awaited()
    session.flush.assert_not_awaited()
    assert workspace.name == "Existing"


@pytest.mark.asyncio
async def test_update_workspace_rejects_unknown_fields():
    workspace = SimpleNamespace(
        id=uuid4(),
        name="Existing",
        description=None,
        timezone="UTC",
    )
    service = WorkspaceService()
    service.repository = SimpleNamespace(
        get_workspace=AsyncMock(return_value=workspace),
        get_workspace_for_update=AsyncMock(return_value=workspace),
        add_audit_log=AsyncMock(),
    )
    service.authorization = SimpleNamespace(
        authorize=AsyncMock(return_value=SimpleNamespace(role="owner")),
    )
    session = SimpleNamespace(flush=AsyncMock())

    with pytest.raises(ValueError, match="Invalid workspace update fields"):
        await service.update_workspace(
            session,
            actor_id=uuid4(),
            workspace_id=workspace.id,
            changes={"is_active": False},
        )

    service.repository.add_audit_log.assert_not_awaited()
