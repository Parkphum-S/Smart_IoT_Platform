"""Mock-based integration tests for authentication API endpoints."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import router as auth_router
from app.api.deps import get_db_session
from app.api.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
)
from app.core.config import Settings, get_settings
from app.core.csrf import verify_csrf_token


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_SECRET = "test-secret-key-that-is-at-least-32-characters"
TEST_ORIGIN = "https://example.com"


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )


@pytest.fixture
def db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def test_client(settings, db_session):
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")

    async def override_db_session():
        yield db_session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = override_db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def login_with_csrf(client, email="user@example.com"):
    """Obtain a pre-login token and prepare trusted-origin headers."""
    csrf_response = client.get("/api/v1/auth/csrf")
    assert csrf_response.status_code == 200

    token = csrf_response.json()["csrf_token"]

    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-password"},
        headers={
            "Origin": TEST_ORIGIN,
            CSRF_HEADER_NAME: token,
        },
    )


def test_issue_csrf_token_sets_cookie_and_returns_token(test_client):
    response = test_client.get("/api/v1/auth/csrf")

    assert response.status_code == 200

    token = response.json()["csrf_token"]
    cookie = response.cookies.get(CSRF_COOKIE_NAME)

    assert token == cookie
    assert verify_csrf_token(token, TEST_SECRET)
    assert f"{CSRF_COOKIE_NAME}=" in response.headers["set-cookie"]
    assert "httponly" not in response.headers["set-cookie"].lower()


def test_login_success_sets_session_and_bound_csrf_cookie(
    test_client, db_session, monkeypatch
):
    from app.api import auth as auth_module

    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        display_name="Test User",
        is_active=True,
    )

    authentication_service = SimpleNamespace(
        authenticate=AsyncMock(return_value=user)
    )

    session_service = SimpleNamespace(
        create_session=AsyncMock(
            return_value=("raw-session-token", SimpleNamespace())
        )
    )

    monkeypatch.setattr(
        auth_module,
        "AuthenticationService",
        lambda: authentication_service,
    )
    monkeypatch.setattr(
        auth_module,
        "SessionService",
        lambda settings: session_service,
    )

    response = login_with_csrf(test_client)

    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email
    assert response.json()["user"]["display_name"] == user.display_name

    assert test_client.cookies.get(SESSION_COOKIE_NAME) == "raw-session-token"

    csrf_token = test_client.cookies.get(CSRF_COOKIE_NAME)
    assert verify_csrf_token(
        csrf_token,
        TEST_SECRET,
        session_binding="raw-session-token",
    )

    assert "httponly" in response.headers["set-cookie"].lower()
    authentication_service.authenticate.assert_awaited_once()
    session_service.create_session.assert_awaited_once()
    db_session.commit.assert_not_awaited()


def test_login_rejects_invalid_credentials(
    test_client, db_session, monkeypatch
):
    from app.api import auth as auth_module

    authentication_service = SimpleNamespace(
        authenticate=AsyncMock(return_value=None)
    )

    monkeypatch.setattr(
        auth_module,
        "AuthenticationService",
        lambda: authentication_service,
    )

    response = login_with_csrf(test_client)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."
    db_session.commit.assert_not_awaited()


def test_login_rejects_missing_csrf_token(test_client, monkeypatch):
    from app.api import auth as auth_module

    authentication_service = SimpleNamespace(
        authenticate=AsyncMock()
    )

    monkeypatch.setattr(
        auth_module,
        "AuthenticationService",
        lambda: authentication_service,
    )

    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "correct-password",
        },
        headers={"Origin": TEST_ORIGIN},
    )

    assert response.status_code == 403
    authentication_service.authenticate.assert_not_awaited()


def test_get_current_user_returns_authenticated_user(
    test_client, db_session, monkeypatch
):
    from app.api import deps as deps_module

    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="user@example.com",
        display_name="Test User",
        is_active=True,
    )
    user_session = SimpleNamespace(user_id=user_id)

    session_service = SimpleNamespace(
        validate_session=AsyncMock(return_value=user_session)
    )

    monkeypatch.setattr(
        deps_module,
        "SessionService",
        lambda settings: session_service,
    )

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = user
    db_session.execute.return_value = query_result

    test_client.cookies.set(SESSION_COOKIE_NAME, "valid-session-token")

    response = test_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["display_name"] == user.display_name
    session_service.validate_session.assert_awaited_once()
    db_session.commit.assert_not_awaited()


def test_get_current_user_rejects_missing_session(test_client):
    response = test_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_logout_revokes_session_and_clears_cookies(
    test_client, db_session, monkeypatch
):
    from app.api import auth as auth_module

    session_service = SimpleNamespace(
        revoke_session=AsyncMock(return_value=True)
    )

    monkeypatch.setattr(
        auth_module,
        "SessionService",
        lambda settings: session_service,
    )

    session_token = "valid-session-token"

    from app.core.csrf import generate_csrf_token

    csrf_token = generate_csrf_token(
        TEST_SECRET,
        session_binding=session_token,
    )

    test_client.cookies.set(SESSION_COOKIE_NAME, session_token)
    test_client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

    response = test_client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": TEST_ORIGIN,
            CSRF_HEADER_NAME: csrf_token,
        },
    )

    assert response.status_code == 204
    session_service.revoke_session.assert_awaited_once()
    db_session.commit.assert_not_awaited()
    assert SESSION_COOKIE_NAME in response.headers["set-cookie"]
    assert CSRF_COOKIE_NAME in response.headers["set-cookie"]
