"""Unit tests for the user session service."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.session_tokens import hash_session_token
from app.modules.users.services.session_service import SessionService


@pytest.fixture
def service():
    settings = SimpleNamespace(
        session_absolute_lifetime_seconds=604800,
        session_idle_timeout_seconds=1800,
        session_activity_update_interval_seconds=300,
    )
    instance = SessionService(settings)
    instance.repository = AsyncMock()
    return instance


@pytest.fixture
def now():
    return datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def active_session(now):
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        token_hash=hash_session_token("test-token"),
        created_at=now - timedelta(minutes=10),
        last_seen_at=now - timedelta(minutes=2),
        expires_at=now + timedelta(days=7),
        revoked_at=None,
    )


@pytest.mark.asyncio
async def test_create_session_generates_and_stores_token(
    service, now, monkeypatch
):
    monkeypatch.setattr(
        SessionService, "_utc_now", staticmethod(lambda: now)
    )
    monkeypatch.setattr(
        "app.modules.users.services.session_service.generate_session_token",
        lambda: "new-test-token",
    )
    expected = SimpleNamespace(id=uuid4())
    service.repository.create_session.return_value = expected

    raw_token, result = await service.create_session(
        MagicMock(), user_id=uuid4()
    )

    assert raw_token == "new-test-token"
    assert result is expected
    service.repository.create_session.assert_awaited_once()
    kwargs = service.repository.create_session.await_args.kwargs
    assert kwargs["token_hash"] == hash_session_token(raw_token)
    assert kwargs["expires_at"] == now + timedelta(days=7)


@pytest.mark.asyncio
async def test_validate_session_accepts_active_session(
    service, active_session, now, monkeypatch
):
    monkeypatch.setattr(
        SessionService, "_utc_now", staticmethod(lambda: now)
    )
    service.repository.get_session_by_token_hash.return_value = active_session

    db_session = MagicMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = True
    db_session.execute = AsyncMock(return_value=user_result)

    result = await service.validate_session(
        db_session, raw_token="test-token"
    )

    assert result is active_session
    service.repository.update_last_seen.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_session_rejects_expired_session(
    service, active_session, now, monkeypatch
):
    monkeypatch.setattr(
        SessionService, "_utc_now", staticmethod(lambda: now)
    )
    active_session.expires_at = now - timedelta(seconds=1)
    service.repository.get_session_by_token_hash.return_value = active_session

    result = await service.validate_session(
        MagicMock(), raw_token="test-token"
    )

    assert result is None
    service.repository.revoke_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_session_rejects_idle_session(
    service, active_session, now, monkeypatch
):
    monkeypatch.setattr(
        SessionService, "_utc_now", staticmethod(lambda: now)
    )
    active_session.last_seen_at = now - timedelta(minutes=31)
    service.repository.get_session_by_token_hash.return_value = active_session

    result = await service.validate_session(
        MagicMock(), raw_token="test-token"
    )

    assert result is None
    service.repository.revoke_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_session_rejects_inactive_user(
    service, active_session, now, monkeypatch
):
    monkeypatch.setattr(
        SessionService, "_utc_now", staticmethod(lambda: now)
    )
    service.repository.get_session_by_token_hash.return_value = active_session

    db_session = MagicMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = False
    db_session.execute = AsyncMock(return_value=user_result)

    result = await service.validate_session(
        db_session, raw_token="test-token"
    )

    assert result is None
    service.repository.revoke_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_session_updates_old_activity(
    service, active_session, now, monkeypatch
):
    monkeypatch.setattr(
        SessionService, "_utc_now", staticmethod(lambda: now)
    )
    active_session.last_seen_at = now - timedelta(minutes=6)
    service.repository.get_session_by_token_hash.return_value = active_session
    service.repository.update_last_seen.return_value = True

    db_session = MagicMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = True
    db_session.execute = AsyncMock(return_value=user_result)

    result = await service.validate_session(
        db_session, raw_token="test-token"
    )

    assert result is active_session
    assert active_session.last_seen_at == now
    service.repository.update_last_seen.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_session_uses_token_hash(service, active_session):
    service.repository.get_session_by_token_hash.return_value = active_session
    service.repository.revoke_session.return_value = True

    db_session = MagicMock()

    result = await service.revoke_session(
        db_session, raw_token="test-token"
    )

    assert result is True
    service.repository.get_session_by_token_hash.assert_awaited_once_with(
        db_session, hash_session_token("test-token")
    )


@pytest.mark.asyncio
async def test_revoke_all_user_sessions(service):
    user_id = uuid4()
    service.repository.revoke_all_user_sessions.return_value = 2

    result = await service.revoke_all_user_sessions(
        MagicMock(), user_id=user_id
    )

    assert result == 2
    service.repository.revoke_all_user_sessions.assert_awaited_once()
