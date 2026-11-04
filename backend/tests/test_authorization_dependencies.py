from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_user,
    get_db_session,
    require_permission,
)
from app.modules.users.services.authorization.authorization_service import (
    PermissionDenied,
    WorkspaceMembershipNotFound,
)


@pytest.fixture
def dependency_test_app(monkeypatch):
    from app.api import deps as deps_module

    user = SimpleNamespace(id=uuid4(), is_active=True)
    membership = SimpleNamespace(
        role="viewer",
        workspace_id=uuid4(),
        user_id=user.id,
        is_active=True,
    )

    authorization_service = SimpleNamespace(
        authorize=AsyncMock(return_value=membership)
    )

    monkeypatch.setattr(
        deps_module,
        "AuthorizationService",
        lambda: authorization_service,
    )

    app = FastAPI()

    @app.get("/workspaces/{workspace_id}/test")
    async def protected_endpoint(
        authorized_membership=Depends(
            require_permission("workspace.read")
        ),
    ):
        return {"role": authorized_membership.role}

    async def override_current_user():
        return user

    async def override_db_session():
        yield object()

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = override_db_session

    with TestClient(app) as client:
        yield client, authorization_service, user, membership

    app.dependency_overrides.clear()


def test_permission_dependency_allows_authorized_member(
    dependency_test_app,
):
    client, authorization_service, user, membership = dependency_test_app

    response = client.get(
        f"/workspaces/{membership.workspace_id}/test"
    )

    assert response.status_code == 200
    assert response.json() == {"role": "viewer"}
    authorization_service.authorize.assert_awaited_once()


def test_permission_dependency_returns_404_without_membership(
    dependency_test_app,
):
    client, authorization_service, user, membership = dependency_test_app
    authorization_service.authorize.side_effect = (
        WorkspaceMembershipNotFound()
    )

    response = client.get(
        f"/workspaces/{membership.workspace_id}/test"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace not found."


def test_permission_dependency_returns_403_without_permission(
    dependency_test_app,
):
    client, authorization_service, user, membership = dependency_test_app
    authorization_service.authorize.side_effect = PermissionDenied()

    response = client.get(
        f"/workspaces/{membership.workspace_id}/test"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied."


def test_permission_dependency_passes_authenticated_user_and_workspace(
    dependency_test_app,
):
    client, authorization_service, user, membership = dependency_test_app

    response = client.get(
        f"/workspaces/{membership.workspace_id}/test"
    )

    assert response.status_code == 200
    authorization_service.authorize.assert_awaited_once_with(
        ANY,
        user_id=user.id,
        workspace_id=membership.workspace_id,
        permission="workspace.read",
    )
