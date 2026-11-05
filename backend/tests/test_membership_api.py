"""HTTP-level tests for workspace membership endpoints."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db_session
from app.api.memberships import router as memberships_router
from app.api.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
)
from app.core.config import Settings, get_settings
from app.core.csrf import generate_csrf_token
from app.modules.users.services.membership.exceptions import (
    MembershipAlreadyExists,
    MembershipPermissionDenied,
)

TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_SECRET = "test-secret-key-that-is-at-least-32-characters"
TEST_ORIGIN = "https://example.com"
TEST_SESSION = "membership-test-session"


def make_membership(**overrides):
    values = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "user_id": uuid4(),
        "role": "viewer",
        "is_active": True,
        "joined_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_test_client(current_user=None):
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    db_session = AsyncMock()
    app = FastAPI()
    app.include_router(memberships_router, prefix="/api/v1")

    async def override_db_session():
        yield db_session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = override_db_session

    if current_user is not None:
        async def override_current_user():
            return current_user

        app.dependency_overrides[get_current_user] = override_current_user

    return app, db_session


def set_session_csrf(client):
    token = generate_csrf_token(
        TEST_SECRET,
        session_binding=TEST_SESSION,
    )
    client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
    client.cookies.set(CSRF_COOKIE_NAME, token)
    return token


def trusted_headers(token):
    return {
        "Origin": TEST_ORIGIN,
        CSRF_HEADER_NAME: token,
    }


def test_list_members_returns_members(monkeypatch):
    from app.api import memberships as module

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    member = make_membership(workspace_id=workspace_id)
    service = SimpleNamespace(
        list_members=AsyncMock(return_value=[member])
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(user)
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/members"
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(member.id)
    assert response.json()[0]["role"] == "viewer"
    service.list_members.assert_awaited_once()


def test_list_members_can_include_inactive(monkeypatch):
    from app.api import memberships as module

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    service = SimpleNamespace(
        list_members=AsyncMock(return_value=[])
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(user)
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/members",
            params={"include_inactive": "true"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.list_members.await_args.kwargs["include_inactive"] is True


def test_add_member_returns_created_membership(monkeypatch):
    from app.api import memberships as module

    actor_id = uuid4()
    workspace_id = uuid4()
    target_user_id = uuid4()
    member = make_membership(
        workspace_id=workspace_id,
        user_id=target_user_id,
        role="operator",
    )
    service = SimpleNamespace(
        add_member=AsyncMock(return_value=member)
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=actor_id))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            json={"user_id": str(target_user_id), "role": "operator"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["user_id"] == str(target_user_id)
    service.add_member.assert_awaited_once()
    assert service.add_member.await_args.kwargs["actor_id"] == actor_id


def test_add_member_rejects_owner_role(monkeypatch):
    from app.api import memberships as module

    service = SimpleNamespace(add_member=AsyncMock())
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=uuid4()))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"/api/v1/workspaces/{uuid4()}/members",
            json={"user_id": str(uuid4()), "role": "owner"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    service.add_member.assert_not_awaited()


def test_add_member_rejects_missing_csrf(monkeypatch):
    from app.api import memberships as module

    service = SimpleNamespace(add_member=AsyncMock())
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=uuid4()))
    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
        response = client.post(
            f"/api/v1/workspaces/{uuid4()}/members",
            json={"user_id": str(uuid4()), "role": "viewer"},
            headers={"Origin": TEST_ORIGIN},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    service.add_member.assert_not_awaited()


def test_add_member_maps_duplicate_membership_to_conflict(monkeypatch):
    from app.api import memberships as module

    service = SimpleNamespace(
        add_member=AsyncMock(side_effect=MembershipAlreadyExists())
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=uuid4()))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"/api/v1/workspaces/{uuid4()}/members",
            json={"user_id": str(uuid4()), "role": "viewer"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 409


def test_membership_permission_error_maps_to_forbidden(monkeypatch):
    from app.api import memberships as module

    service = SimpleNamespace(
        list_members=AsyncMock(side_effect=MembershipPermissionDenied())
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=uuid4()))
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workspaces/{uuid4()}/members"
        )

    app.dependency_overrides.clear()

    assert response.status_code == 403


def test_transfer_ownership_returns_both_memberships(monkeypatch):
    from app.api import memberships as module

    actor_id = uuid4()
    workspace_id = uuid4()
    target_id = uuid4()

    old_owner = make_membership(
        workspace_id=workspace_id,
        user_id=actor_id,
        role="admin",
    )
    new_owner = make_membership(
        workspace_id=workspace_id,
        user_id=target_id,
        role="owner",
    )
    service = SimpleNamespace(
        transfer_ownership=AsyncMock(
            return_value=(old_owner, new_owner)
        )
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=actor_id))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/members/transfer-ownership",
            json={"target_membership_id": str(new_owner.id)},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["previous_owner"]["role"] == "admin"
    assert response.json()["new_owner"]["role"] == "owner"
    service.transfer_ownership.assert_awaited_once()


def test_membership_api_rejects_unauthenticated_user():
    app, _ = make_test_client()

    async def reject_user():
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    app.dependency_overrides[get_current_user] = reject_user

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workspaces/{uuid4()}/members"
        )

    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_change_member_role_returns_updated_membership(monkeypatch):
    from app.api import memberships as module

    actor_id = uuid4()
    workspace_id = uuid4()
    membership_id = uuid4()
    member = make_membership(
        id=membership_id,
        workspace_id=workspace_id,
        role="admin",
    )
    service = SimpleNamespace(
        change_role=AsyncMock(return_value=member)
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=actor_id))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/members/{membership_id}/role",
            json={"role": "admin"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    service.change_role.assert_awaited_once()
    assert service.change_role.await_args.kwargs == {
        "actor_id": actor_id,
        "workspace_id": workspace_id,
        "membership_id": membership_id,
        "new_role": "admin",
    }


def test_deactivate_member_returns_inactive_membership(monkeypatch):
    from app.api import memberships as module

    actor_id = uuid4()
    workspace_id = uuid4()
    membership_id = uuid4()
    member = make_membership(
        id=membership_id,
        workspace_id=workspace_id,
        is_active=False,
    )
    service = SimpleNamespace(
        deactivate_member=AsyncMock(return_value=member)
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=actor_id))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/members/{membership_id}/deactivate",
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    service.deactivate_member.assert_awaited_once()
    assert service.deactivate_member.await_args.kwargs == {
        "actor_id": actor_id,
        "workspace_id": workspace_id,
        "membership_id": membership_id,
    }


def test_reactivate_member_returns_active_membership(monkeypatch):
    from app.api import memberships as module

    actor_id = uuid4()
    workspace_id = uuid4()
    membership_id = uuid4()
    member = make_membership(
        id=membership_id,
        workspace_id=workspace_id,
        role="operator",
        is_active=True,
    )
    service = SimpleNamespace(
        reactivate_member=AsyncMock(return_value=member)
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    app, _ = make_test_client(SimpleNamespace(id=actor_id))
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/members/{membership_id}/reactivate",
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert response.json()["role"] == "operator"
    service.reactivate_member.assert_awaited_once()
    assert service.reactivate_member.await_args.kwargs == {
        "actor_id": actor_id,
        "workspace_id": workspace_id,
        "membership_id": membership_id,
    }


def test_role_deactivate_and_reactivate_require_csrf(monkeypatch):
    from app.api import memberships as module

    service = SimpleNamespace(
        change_role=AsyncMock(),
        deactivate_member=AsyncMock(),
        reactivate_member=AsyncMock(),
    )
    monkeypatch.setattr(module, "MembershipService", lambda: service)

    workspace_id = uuid4()
    membership_id = uuid4()
    app, _ = make_test_client(SimpleNamespace(id=uuid4()))

    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)

        responses = [
            client.patch(
                f"/api/v1/workspaces/{workspace_id}/members/{membership_id}/role",
                json={"role": "admin"},
                headers={"Origin": TEST_ORIGIN},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/members/{membership_id}/deactivate",
                headers={"Origin": TEST_ORIGIN},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/members/{membership_id}/reactivate",
                headers={"Origin": TEST_ORIGIN},
            ),
        ]

    app.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [403, 403, 403]
    service.change_role.assert_not_awaited()
    service.deactivate_member.assert_not_awaited()
    service.reactivate_member.assert_not_awaited()
