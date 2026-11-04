"""Unit tests for user account repository operations."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.users.repository import UserRepository


@pytest.mark.asyncio
async def test_get_user_by_email_returns_user():
    expected_user = SimpleNamespace(email="user@example.com")
    result = SimpleNamespace(
        scalar_one_or_none=lambda: expected_user
    )
    db_session = AsyncMock()
    db_session.execute.return_value = result

    user = await UserRepository.get_user_by_email(
        db_session,
        "user@example.com",
    )

    assert user is expected_user
    db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_email_normalizes_email():
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db_session = AsyncMock()
    db_session.execute.return_value = result

    user = await UserRepository.get_user_by_email(
        db_session,
        "  USER@EXAMPLE.COM  ",
    )

    assert user is None
    db_session.execute.assert_awaited_once()
