"""Unit tests for the user session repository."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.users.repository import UserSessionRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_session_adds_and_flushes_record(mock_session):
    user_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    result = await UserSessionRepository.create_session(
        mock_session,
        user_id=user_id,
        token_hash="a" * 64,
        expires_at=expires_at,
    )

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    assert result.user_id == user_id
    assert result.token_hash == "a" * 64
    assert result.expires_at == expires_at


@pytest.mark.asyncio
async def test_get_session_by_token_hash_returns_record(mock_session):
    expected = SimpleNamespace(token_hash="a" * 64)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = mock_result

    result = await UserSessionRepository.get_session_by_token_hash(
        mock_session,
        "a" * 64,
    )

    assert result is expected
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_by_token_hash_returns_none(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await UserSessionRepository.get_session_by_token_hash(
        mock_session,
        "b" * 64,
    )

    assert result is None


@pytest.mark.asyncio
async def test_update_last_seen_returns_true_when_one_row_is_updated(
    mock_session,
):
    mock_session.execute.return_value = SimpleNamespace(rowcount=1)

    result = await UserSessionRepository.update_last_seen(
        mock_session,
        session_id=uuid4(),
        last_seen_at=datetime.now(timezone.utc),
    )

    assert result is True


@pytest.mark.asyncio
async def test_update_last_seen_returns_false_when_no_row_is_updated(
    mock_session,
):
    mock_session.execute.return_value = SimpleNamespace(rowcount=0)

    result = await UserSessionRepository.update_last_seen(
        mock_session,
        session_id=uuid4(),
        last_seen_at=datetime.now(timezone.utc),
    )

    assert result is False


@pytest.mark.asyncio
async def test_revoke_session_returns_true_when_revoked(mock_session):
    mock_session.execute.return_value = SimpleNamespace(rowcount=1)

    result = await UserSessionRepository.revoke_session(
        mock_session,
        session_id=uuid4(),
        revoked_at=datetime.now(timezone.utc),
    )

    assert result is True


@pytest.mark.asyncio
async def test_revoke_session_returns_false_when_already_revoked(
    mock_session,
):
    mock_session.execute.return_value = SimpleNamespace(rowcount=0)

    result = await UserSessionRepository.revoke_session(
        mock_session,
        session_id=uuid4(),
        revoked_at=datetime.now(timezone.utc),
    )

    assert result is False


@pytest.mark.asyncio
async def test_revoke_all_user_sessions_returns_updated_count(mock_session):
    mock_session.execute.return_value = SimpleNamespace(rowcount=3)

    result = await UserSessionRepository.revoke_all_user_sessions(
        mock_session,
        user_id=uuid4(),
        revoked_at=datetime.now(timezone.utc),
    )

    assert result == 3


@pytest.mark.asyncio
async def test_revoke_all_user_sessions_returns_zero_when_none_updated(
    mock_session,
):
    mock_session.execute.return_value = SimpleNamespace(rowcount=None)

    result = await UserSessionRepository.revoke_all_user_sessions(
        mock_session,
        user_id=uuid4(),
        revoked_at=datetime.now(timezone.utc),
    )

    assert result == 0
