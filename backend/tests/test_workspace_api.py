from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db_session
from app.api.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
)
from app.api.workspaces import router as workspaces_router
from app.core.config import Settings, get_settings
from app.core.csrf import generate_csrf_token


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_SECRET = "test-secret-key-that-is-at-least-32-characters"
TEST_ORIGIN = "https://example.com"
TEST_SESSION = "workspace-test-session"


def make_test_client(settings, db_session, current_user=None):
    app = FastAPI()
    app.include_router(workspaces_router, prefix="/api/v1")

    async def override_db_session():
        yield db_session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = override_db_session

    if current_user is not None:
        async def override_current_user():
            return current_user

        app.dependency_overrides[get_current_user] = override_current_user

    return app


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


def test_create_workspace_returns_owner_membership(monkeypatch):
    from app.api import workspaces as workspaces_module

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    db_session = AsyncMock()
    current_user = SimpleNamespace(
        id=uuid4(),
        email="creator@example.com",
        display_name="Workspace Creator",
        is_active=True,
    )

    workspace_id = uuid4()
    membership = SimpleNamespace(role="owner", is_active=True)
    workspace = SimpleNamespace(
        id=workspace_id,
        name="My Smart Building",
        description="Building IoT Management",
        timezone="Asia/Bangkok",
    )
    service = SimpleNamespace(
        create_workspace=AsyncMock(return_value=(workspace, membership))
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, db_session, current_user)
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            "/api/v1/workspaces",
            json={
                "name": "My Smart Building",
                "description": "Building IoT Management",
                "timezone": "Asia/Bangkok",
            },
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "id": str(workspace_id),
        "name": "My Smart Building",
        "description": "Building IoT Management",
        "timezone": "Asia/Bangkok",
        "role": "owner",
        "is_active": True,
    }
    service.create_workspace.assert_awaited_once()
    assert service.create_workspace.await_args.kwargs["creator_id"] == current_user.id


def test_create_workspace_rejects_missing_csrf(monkeypatch):
    from app.api import workspaces as workspaces_module

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    service = SimpleNamespace(create_workspace=AsyncMock())
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
        response = client.post(
            "/api/v1/workspaces",
            json={"name": "My Workspace"},
            headers={"Origin": TEST_ORIGIN},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    service.create_workspace.assert_not_awaited()


def test_create_workspace_rejects_client_supplied_role():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    app = make_test_client(settings, AsyncMock(), current_user)

    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            "/api/v1/workspaces",
            json={"name": "My Workspace", "role": "admin"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_create_workspace_rejects_invalid_timezone():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    app = make_test_client(settings, AsyncMock(), current_user)

    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            "/api/v1/workspaces",
            json={"name": "My Workspace", "timezone": "Not/A_Timezone"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_create_workspace_rejects_unauthenticated_user():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )

    app = make_test_client(settings, AsyncMock())

    async def reject_user():
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    app.dependency_overrides[get_current_user] = reject_user

    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.post(
            "/api/v1/workspaces",
            json={"name": "My Workspace"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 401


def test_get_workspace_returns_details(monkeypatch):
    from app.api import workspaces as workspaces_module

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    workspace = SimpleNamespace(
        id=workspace_id,
        name="Building A",
        description="Smart building",
        timezone="Asia/Bangkok",
    )
    service = SimpleNamespace(
        get_workspace=AsyncMock(return_value=workspace),
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/workspaces/{workspace_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(workspace_id),
        "name": "Building A",
        "description": "Smart building",
        "timezone": "Asia/Bangkok",
    }
    service.get_workspace.assert_awaited_once()


def test_get_workspace_rejects_user_without_permission(monkeypatch):
    from app.api import workspaces as workspaces_module
    from app.modules.users.services.workspace_service import (
        WorkspacePermissionDenied,
    )

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    service = SimpleNamespace(
        get_workspace=AsyncMock(side_effect=WorkspacePermissionDenied),
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/workspaces/{uuid4()}")

    app.dependency_overrides.clear()

    assert response.status_code == 403


def test_update_workspace_returns_updated_details(monkeypatch):
    from app.api import workspaces as workspaces_module

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    workspace = SimpleNamespace(
        id=workspace_id,
        name="Building B",
        description="Updated description",
        timezone="Asia/Bangkok",
    )
    service = SimpleNamespace(
        update_workspace=AsyncMock(return_value=workspace),
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}",
            json={
                "name": "Building B",
                "description": "Updated description",
            },
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["name"] == "Building B"
    assert response.json()["description"] == "Updated description"
    service.update_workspace.assert_awaited_once()
    assert service.update_workspace.await_args.kwargs["changes"] == {
        "name": "Building B",
        "description": "Updated description",
    }


def test_update_workspace_rejects_missing_csrf(monkeypatch):
    from app.api import workspaces as workspaces_module

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    service = SimpleNamespace(update_workspace=AsyncMock())
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
        response = client.patch(
            f"/api/v1/workspaces/{uuid4()}",
            json={"name": "Changed"},
            headers={"Origin": TEST_ORIGIN},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    service.update_workspace.assert_not_awaited()


def test_update_workspace_rejects_invalid_timezone():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    app = make_test_client(settings, AsyncMock(), current_user)

    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{uuid4()}",
            json={"timezone": "Invalid/Timezone"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_update_workspace_rejects_empty_payload():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    app = make_test_client(settings, AsyncMock(), current_user)

    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{uuid4()}",
            json={},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_get_workspace_returns_404_when_missing(monkeypatch):
    from app.api import workspaces as workspaces_module
    from app.modules.users.services.workspace_service import WorkspaceNotFound

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    service = SimpleNamespace(
        get_workspace=AsyncMock(side_effect=WorkspaceNotFound),
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/workspaces/{uuid4()}")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    service.get_workspace.assert_awaited_once()


def test_update_workspace_returns_404_when_missing(monkeypatch):
    from app.api import workspaces as workspaces_module
    from app.modules.users.services.workspace_service import WorkspaceNotFound

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    service = SimpleNamespace(
        update_workspace=AsyncMock(side_effect=WorkspaceNotFound),
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{uuid4()}",
            json={"name": "Updated"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    service.update_workspace.assert_awaited_once()


def test_update_workspace_accepts_valid_timezone(monkeypatch):
    from app.api import workspaces as workspaces_module

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    workspace = SimpleNamespace(
        id=workspace_id,
        name="Building C",
        description=None,
        timezone="Asia/Bangkok",
    )
    service = SimpleNamespace(
        update_workspace=AsyncMock(return_value=workspace),
    )
    monkeypatch.setattr(workspaces_module, "WorkspaceService", lambda: service)

    app = make_test_client(settings, AsyncMock(), current_user)
    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}",
            json={"timezone": "Asia/Bangkok"},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["timezone"] == "Asia/Bangkok"
    assert service.update_workspace.await_args.kwargs["changes"] == {
        "timezone": "Asia/Bangkok",
    }


def test_update_workspace_rejects_null_name():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    current_user = SimpleNamespace(id=uuid4())
    app = make_test_client(settings, AsyncMock(), current_user)

    with TestClient(app) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"/api/v1/workspaces/{uuid4()}",
            json={"name": None},
            headers=trusted_headers(token),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422
