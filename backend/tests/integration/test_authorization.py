"""Integration tests for database-backed workspace authorization."""

import pytest

from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import Permission
from factories import create_membership, create_user, create_workspace_with_owner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "permission", "allowed"),
    [
        ("owner", Permission.WORKSPACE_DELETE, True),
        ("owner", Permission.OWNERSHIP_TRANSFER, True),
        ("admin", Permission.WORKSPACE_DELETE, False),
        ("admin", Permission.MEMBERS_INVITE, True),
        ("operator", Permission.DEVICES_CONTROL, True),
        ("operator", Permission.MEMBERS_INVITE, False),
        ("viewer", Permission.TELEMETRY_READ, True),
        ("viewer", Permission.DEVICES_CONTROL, False),
    ],
)
async def test_authorization_uses_persisted_membership_role(
    db_session, role, permission, allowed
):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    service = AuthorizationService()

    if role == "owner":
        subject = owner
    else:
        subject = await create_user(db_session)
        await create_membership(
            db_session,
            workspace=workspace,
            user=subject,
            role=role,
        )

    if allowed:
        membership = await service.authorize(
            db_session,
            user_id=subject.id,
            workspace_id=workspace.id,
            permission=permission,
        )
        assert membership.role == role
    else:
        with pytest.raises(PermissionDenied):
            await service.authorize(
                db_session,
                user_id=subject.id,
                workspace_id=workspace.id,
                permission=permission,
            )


@pytest.mark.asyncio
async def test_authorization_rejects_inactive_membership(db_session):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    subject = await create_user(db_session)
    await create_membership(
        db_session,
        workspace=workspace,
        user=subject,
        role="viewer",
        is_active=False,
    )

    service = AuthorizationService()

    with pytest.raises(WorkspaceMembershipNotFound):
        await service.authorize(
            db_session,
            user_id=subject.id,
            workspace_id=workspace.id,
            permission=Permission.WORKSPACE_READ,
        )


@pytest.mark.asyncio
async def test_authorization_rejects_inactive_platform_user(db_session):
    workspace, _, _ = await create_workspace_with_owner(db_session)
    subject = await create_user(db_session, is_active=False)
    await create_membership(
        db_session,
        workspace=workspace,
        user=subject,
        role="viewer",
    )

    service = AuthorizationService()

    with pytest.raises(WorkspaceMembershipNotFound):
        await service.authorize(
            db_session,
            user_id=subject.id,
            workspace_id=workspace.id,
            permission=Permission.WORKSPACE_READ,
        )


@pytest.mark.asyncio
async def test_authorization_rejects_unknown_permission(db_session):
    workspace, owner, _ = await create_workspace_with_owner(db_session)
    service = AuthorizationService()

    with pytest.raises(PermissionDenied):
        await service.authorize(
            db_session,
            user_id=owner.id,
            workspace_id=workspace.id,
            permission="unknown.permission",
        )
