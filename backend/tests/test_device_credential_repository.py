"""Unit tests for workspace-scoped device credential persistence."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.devices.services.device_credential_repository import (
    DeviceCredentialRepository,
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
async def test_get_by_identifier_is_broker_scoped_and_supports_row_lock(
    mock_session,
):
    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    credential = await (
        DeviceCredentialRepository().get_by_identifier(
            mock_session,
            broker_key="main",
            credential_identifier="device-credential-01",
            for_update=True,
        )
    )

    sql, params = compiled_statement(mock_session)

    assert credential is expected
    assert "device_credentials.broker_key =" in sql
    assert "device_credentials.credential_identifier =" in sql
    assert "for update" in sql
    assert "main" in params.values()
    assert "device-credential-01" in params.values()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_for_authentication_requires_eligible_device_and_hash(
    mock_session,
):
    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    credential = (
        await DeviceCredentialRepository().get_for_authentication(
            mock_session,
            broker_key="main",
            credential_identifier="device-credential-01",
        )
    )

    sql, params = compiled_statement(mock_session)

    assert credential is expected
    assert "join devices" in sql
    assert (
        "devices.workspace_id = device_credentials.workspace_id"
        in sql
    )
    assert "devices.id = device_credentials.device_id" in sql
    assert "device_credentials.credential_status =" in sql
    assert "device_credentials.secret_hash is not null" in sql
    assert "device_credentials.expires_at > now()" in sql
    assert "devices.is_enabled is true" in sql
    assert "devices.lifecycle_status =" in sql

    assert "main" in params.values()
    assert "device-credential-01" in params.values()
    assert "active" in params.values()

    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_list_for_device_is_workspace_scoped(mock_session):
    workspace_id = uuid4()
    device_id = uuid4()
    expected = [MagicMock(), MagicMock()]

    scalars = MagicMock()
    scalars.all.return_value = expected

    result = MagicMock()
    result.scalars.return_value = scalars
    mock_session.execute.return_value = result

    credentials = await DeviceCredentialRepository().list_for_device(
        mock_session,
        workspace_id=workspace_id,
        device_id=device_id,
    )

    sql, params = compiled_statement(mock_session)

    assert credentials == expected
    assert "device_credentials.workspace_id =" in sql
    assert "device_credentials.device_id =" in sql
    assert "order by device_credentials.created_at desc" in sql
    assert workspace_id in params.values()
    assert device_id in params.values()


@pytest.mark.asyncio
async def test_create_adds_pending_credential_and_flushes(mock_session):
    workspace_id = uuid4()
    device_id = uuid4()

    credential = await DeviceCredentialRepository().create(
        mock_session,
        workspace_id=workspace_id,
        device_id=device_id,
        broker_key="main",
        credential_identifier="credential-01",
        credential_type="password",
        secret_hash="$argon2id$test-hash",
    )

    assert credential.workspace_id == workspace_id
    assert credential.device_id == device_id
    assert credential.broker_key == "main"
    assert credential.credential_identifier == "credential-01"
    assert credential.credential_status == "pending"
    assert credential.secret_hash == "$argon2id$test-hash"
    mock_session.add.assert_called_once_with(credential)
    mock_session.flush.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_activate_accepts_only_pending_credentials(mock_session):
    credential = SimpleNamespace(
        credential_status="pending",
        revoked_at=None,
    )

    result = await DeviceCredentialRepository().activate(
        mock_session,
        credential=credential,
    )

    assert result is credential
    assert credential.credential_status == "active"
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_rejects_revoked_credentials(mock_session):
    credential = SimpleNamespace(
        credential_status="revoked",
        revoked_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="Only pending credentials"):
        await DeviceCredentialRepository().activate(
            mock_session,
            credential=credential,
        )

    assert credential.credential_status == "revoked"
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_sets_terminal_state_and_timestamp(mock_session):
    revoked_at = datetime.now(timezone.utc)
    credential = SimpleNamespace(
        credential_status="active",
        revoked_at=None,
    )

    result = await DeviceCredentialRepository().revoke(
        mock_session,
        credential=credential,
        revoked_at=revoked_at,
    )

    assert result is credential
    assert credential.credential_status == "revoked"
    assert credential.revoked_at == revoked_at
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_rotated_updates_timestamp(mock_session):
    rotated_at = datetime.now(timezone.utc)
    credential = SimpleNamespace(rotated_at=None)

    result = await DeviceCredentialRepository().mark_rotated(
        mock_session,
        credential=credential,
        rotated_at=rotated_at,
    )

    assert result is credential
    assert credential.rotated_at == rotated_at
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_last_used_updates_timestamp(mock_session):
    last_used_at = datetime.now(timezone.utc)
    credential = SimpleNamespace(last_used_at=None)

    result = await DeviceCredentialRepository().update_last_used(
        mock_session,
        credential=credential,
        last_used_at=last_used_at,
    )

    assert result is credential
    assert credential.last_used_at == last_used_at
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_for_enrollment_scopes_all_device_identity_fields(
    mock_session,
):
    workspace_id = uuid4()
    device_id = uuid4()
    expected = MagicMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    credential = (
        await DeviceCredentialRepository().get_for_enrollment(
            mock_session,
            workspace_id=workspace_id,
            device_id=device_id,
            broker_key="main",
            credential_identifier="dc_enrollment_01",
        )
    )

    sql, params = compiled_statement(mock_session)

    assert credential is expected
    assert "device_credentials.workspace_id =" in sql
    assert "device_credentials.device_id =" in sql
    assert "device_credentials.broker_key =" in sql
    assert "device_credentials.credential_identifier =" in sql
    assert "for update" not in sql

    assert workspace_id in params.values()
    assert device_id in params.values()
    assert "main" in params.values()
    assert "dc_enrollment_01" in params.values()


@pytest.mark.asyncio
async def test_get_for_enrollment_supports_row_lock(mock_session):
    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    credential = (
        await DeviceCredentialRepository().get_for_enrollment(
            mock_session,
            workspace_id=uuid4(),
            device_id=uuid4(),
            broker_key="main",
            credential_identifier="dc_enrollment_02",
            for_update=True,
        )
    )

    sql, _ = compiled_statement(mock_session)

    assert credential is expected
    assert "for update" in sql
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_for_enrollment_returns_none_when_not_found(
    mock_session,
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result

    credential = (
        await DeviceCredentialRepository().get_for_enrollment(
            mock_session,
            workspace_id=uuid4(),
            device_id=uuid4(),
            broker_key="main",
            credential_identifier="dc_missing",
            for_update=True,
        )
    )

    assert credential is None
