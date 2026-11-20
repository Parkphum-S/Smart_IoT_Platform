"""Unit tests for device bootstrap token persistence."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.devices.services.device_bootstrap_token_repository import (
    DeviceBootstrapTokenRepository,
)


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


def compiled_statement(session):
    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    return str(compiled).lower(), compiled.params


@pytest.mark.asyncio
async def test_create_stores_hash_only_and_flushes(mock_session):
    workspace_id = uuid4()
    device_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    token_hash = "a" * 64

    token = await DeviceBootstrapTokenRepository().create(
        mock_session,
        workspace_id=workspace_id,
        device_id=device_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    assert token.workspace_id == workspace_id
    assert token.device_id == device_id
    assert token.token_hash == token_hash
    assert token.expires_at == expires_at
    assert token.consumed_at is None
    assert token.revoked_at is None

    mock_session.add.assert_called_once_with(token)
    mock_session.flush.assert_awaited_once()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_hash_supports_row_lock(mock_session):
    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    token = await DeviceBootstrapTokenRepository().get_by_hash(
        mock_session,
        token_hash="b" * 64,
        for_update=True,
    )

    sql, params = compiled_statement(mock_session)

    assert token is expected
    assert "device_bootstrap_tokens.token_hash =" in sql
    assert "for update" in sql
    assert "b" * 64 in params.values()



@pytest.mark.asyncio
async def test_get_for_validation_checks_device_and_token_state(
    mock_session,
):
    token_hash = "c" * 64

    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    token = await DeviceBootstrapTokenRepository().get_for_validation(
        mock_session,
        token_hash=token_hash,
        for_update=True,
    )

    sql, params = compiled_statement(mock_session)

    assert token is expected
    assert "join devices" in sql
    assert (
        "devices.workspace_id = device_bootstrap_tokens.workspace_id"
        in sql
    )
    assert "devices.id = device_bootstrap_tokens.device_id" in sql
    assert "device_bootstrap_tokens.token_hash =" in sql
    assert "device_bootstrap_tokens.expires_at > now()" in sql
    assert "device_bootstrap_tokens.consumed_at is null" in sql
    assert "device_bootstrap_tokens.revoked_at is null" in sql
    assert "devices.is_enabled is true" in sql
    assert "devices.lifecycle_status =" in sql
    assert "for update of device_bootstrap_tokens" in sql

    assert token_hash in params.values()
    assert "pending_provisioning" in params.values()


@pytest.mark.asyncio
async def test_get_for_validation_returns_none_when_not_found(
    mock_session,
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result

    token = await DeviceBootstrapTokenRepository().get_for_validation(
        mock_session,
        token_hash="d" * 64,
    )

    assert token is None


@pytest.mark.asyncio
async def test_consume_marks_token_once(mock_session):
    consumed_at = datetime.now(timezone.utc)
    token = SimpleNamespace(
        id=uuid4(),
        consumed_at=None,
        revoked_at=None,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = token.id
    mock_session.execute.return_value = result

    updated = await DeviceBootstrapTokenRepository().consume(
        mock_session,
        token=token,
        consumed_at=consumed_at,
    )

    sql, params = compiled_statement(mock_session)

    assert updated is token
    assert token.consumed_at == consumed_at
    assert "update device_bootstrap_tokens" in sql
    assert "device_bootstrap_tokens.consumed_at is null" in sql
    assert "device_bootstrap_tokens.revoked_at is null" in sql
    assert "device_bootstrap_tokens.expires_at > now()" in sql
    assert "returning device_bootstrap_tokens.id" in sql
    assert token.id in params.values()

    mock_session.execute.assert_awaited_once()
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_rejects_update_without_returned_id(mock_session):
    token = SimpleNamespace(
        id=uuid4(),
        consumed_at=None,
        revoked_at=None,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result

    with pytest.raises(
        ValueError,
        match="expired, consumed, or revoked",
    ):
        await DeviceBootstrapTokenRepository().consume(
            mock_session,
            token=token,
            consumed_at=datetime.now(timezone.utc),
        )

    mock_session.execute.assert_awaited_once()
    mock_session.flush.assert_not_awaited()
    assert token.consumed_at is None


@pytest.mark.asyncio
async def test_revoke_marks_unused_token(mock_session):
    revoked_at = datetime.now(timezone.utc)
    token = SimpleNamespace(
        id=uuid4(),
        consumed_at=None,
        revoked_at=None,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = token.id
    mock_session.execute.return_value = result

    updated = await DeviceBootstrapTokenRepository().revoke(
        mock_session,
        token=token,
        revoked_at=revoked_at,
    )

    sql, params = compiled_statement(mock_session)

    assert updated is token
    assert token.revoked_at == revoked_at
    assert "update device_bootstrap_tokens" in sql
    assert "device_bootstrap_tokens.consumed_at is null" in sql
    assert "device_bootstrap_tokens.revoked_at is null" in sql
    assert "returning device_bootstrap_tokens.id" in sql
    assert token.id in params.values()

    mock_session.execute.assert_awaited_once()
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_rejects_update_without_returned_id(mock_session):
    token = SimpleNamespace(
        id=uuid4(),
        consumed_at=None,
        revoked_at=None,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result

    with pytest.raises(
        ValueError,
        match="already consumed or revoked",
    ):
        await DeviceBootstrapTokenRepository().revoke(
            mock_session,
            token=token,
            revoked_at=datetime.now(timezone.utc),
        )

    mock_session.execute.assert_awaited_once()
    mock_session.flush.assert_not_awaited()
    assert token.revoked_at is None


@pytest.mark.asyncio
async def test_get_scopes_token_to_workspace(mock_session):
    workspace_id = uuid4()
    token_id = uuid4()

    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    token = await DeviceBootstrapTokenRepository().get(
        mock_session,
        workspace_id=workspace_id,
        token_id=token_id,
    )

    sql, params = compiled_statement(mock_session)

    assert token is expected
    assert "device_bootstrap_tokens.workspace_id =" in sql
    assert "device_bootstrap_tokens.id =" in sql
    assert workspace_id in params.values()
    assert token_id in params.values()
    assert "for update" not in sql


@pytest.mark.asyncio
async def test_get_supports_row_lock(mock_session):
    workspace_id = uuid4()
    token_id = uuid4()

    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    token = await DeviceBootstrapTokenRepository().get(
        mock_session,
        workspace_id=workspace_id,
        token_id=token_id,
        for_update=True,
    )

    sql, params = compiled_statement(mock_session)

    assert token is expected
    assert "for update" in sql
    assert workspace_id in params.values()
    assert token_id in params.values()


@pytest.mark.asyncio
async def test_get_returns_none_when_token_not_in_workspace(
    mock_session,
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result

    token = await DeviceBootstrapTokenRepository().get(
        mock_session,
        workspace_id=uuid4(),
        token_id=uuid4(),
    )

    assert token is None
