"""Unit tests for user authentication service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.users.services import authentication_service as auth_module
from app.modules.users.services.authentication_service import AuthenticationService


@pytest.fixture
def db_session():
    return AsyncMock()


@pytest.fixture
def auth_service():
    return AuthenticationService()


@pytest.mark.asyncio
async def test_authenticate_returns_active_user(
    db_session, auth_service, monkeypatch
):
    user = SimpleNamespace(
        email="user@example.com",
        password_hash="stored-hash",
        is_active=True,
    )
    monkeypatch.setattr(
        auth_service.repository,
        "get_user_by_email",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(auth_module, "verify_password", lambda *args: True)
    monkeypatch.setattr(auth_module, "needs_rehash", lambda _: False)

    result = await auth_service.authenticate(
        db_session,
        email="user@example.com",
        password="correct-password",
    )

    assert result is user
    db_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_rejects_incorrect_password(
    db_session, auth_service, monkeypatch
):
    user = SimpleNamespace(
        email="user@example.com",
        password_hash="stored-hash",
        is_active=True,
    )
    monkeypatch.setattr(
        auth_service.repository,
        "get_user_by_email",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(auth_module, "verify_password", lambda *args: False)

    result = await auth_service.authenticate(
        db_session,
        email="user@example.com",
        password="wrong-password",
    )

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_rejects_inactive_user(
    db_session, auth_service, monkeypatch
):
    user = SimpleNamespace(
        email="user@example.com",
        password_hash="stored-hash",
        is_active=False,
    )
    monkeypatch.setattr(
        auth_service.repository,
        "get_user_by_email",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(auth_module, "verify_password", lambda *args: True)

    result = await auth_service.authenticate(
        db_session,
        email="user@example.com",
        password="correct-password",
    )

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_returns_none_when_user_not_found(
    db_session, auth_service, monkeypatch
):
    monkeypatch.setattr(
        auth_service.repository,
        "get_user_by_email",
        AsyncMock(return_value=None),
    )

    result = await auth_service.authenticate(
        db_session,
        email="missing@example.com",
        password="some-password",
    )

    assert result is None
