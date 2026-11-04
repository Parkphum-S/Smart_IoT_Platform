from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)


@pytest.fixture
def service(monkeypatch):
    authorization_service = AuthorizationService()
    repository_mock = AsyncMock()
    monkeypatch.setattr(
        authorization_service.repository,
        "get_active_membership",
        repository_mock,
    )
    return authorization_service, repository_mock


@pytest.fixture
def identifiers():
    return {
        "user_id": uuid4(),
        "workspace_id": uuid4(),
    }


@pytest.mark.asyncio
async def test_authorize_returns_membership_when_permission_granted(
    service, identifiers
):
    authorization_service, repository_mock = service
    membership = SimpleNamespace(role="viewer", is_active=True)
    repository_mock.return_value = membership

    result = await authorization_service.authorize(
        None,
        **identifiers,
        permission="workspace.read",
    )

    assert result is membership
    repository_mock.assert_awaited_once_with(
        None,
        **identifiers,
    )


@pytest.mark.asyncio
async def test_authorize_rejects_missing_membership(service, identifiers):
    authorization_service, repository_mock = service
    repository_mock.return_value = None

    with pytest.raises(WorkspaceMembershipNotFound):
        await authorization_service.authorize(
            None,
            **identifiers,
            permission="workspace.read",
        )


@pytest.mark.asyncio
async def test_authorize_rejects_permission_not_granted(
    service, identifiers
):
    authorization_service, repository_mock = service
    repository_mock.return_value = SimpleNamespace(
        role="viewer",
        is_active=True,
    )

    with pytest.raises(PermissionDenied):
        await authorization_service.authorize(
            None,
            **identifiers,
            permission="devices.control",
        )


@pytest.mark.asyncio
async def test_authorize_rejects_unknown_role(service, identifiers):
    authorization_service, repository_mock = service
    repository_mock.return_value = SimpleNamespace(
        role="superadmin",
        is_active=True,
    )

    with pytest.raises(PermissionDenied):
        await authorization_service.authorize(
            None,
            **identifiers,
            permission="workspace.read",
        )


@pytest.mark.asyncio
async def test_authorize_rejects_unknown_permission(
    service, identifiers
):
    authorization_service, repository_mock = service
    repository_mock.return_value = SimpleNamespace(
        role="owner",
        is_active=True,
    )

    with pytest.raises(PermissionDenied):
        await authorization_service.authorize(
            None,
            **identifiers,
            permission="workspace.superuser",
        )


@pytest.mark.asyncio
async def test_authorize_does_not_check_policy_without_membership(
    service, identifiers
):
    authorization_service, repository_mock = service
    repository_mock.return_value = None

    with pytest.raises(WorkspaceMembershipNotFound):
        await authorization_service.authorize(
            None,
            **identifiers,
            permission="workspace.read",
        )

    repository_mock.assert_awaited_once()
