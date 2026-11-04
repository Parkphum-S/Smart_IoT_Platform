from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.users.services.authorization.repository import (
    AuthorizationRepository,
)


@pytest.mark.asyncio
async def test_get_active_membership_scopes_query_to_user_and_workspace():
    user_id = uuid4()
    workspace_id = uuid4()

    membership = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = membership

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await AuthorizationRepository.get_active_membership(
        session,
        user_id=user_id,
        workspace_id=workspace_id,
    )

    assert returned is membership
    session.execute.assert_awaited_once()

    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    params = compiled.params

    assert "join users" in sql
    assert "workspace_members.user_id =" in sql
    assert "workspace_members.workspace_id =" in sql
    assert "workspace_members.is_active is true" in sql
    assert "users.is_active is true" in sql

    assert user_id in params.values()
    assert workspace_id in params.values()

    result.scalar_one_or_none.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_active_membership_returns_none_when_no_active_membership():
    result = Mock()
    result.scalar_one_or_none.return_value = None

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await AuthorizationRepository.get_active_membership(
        session,
        user_id=uuid4(),
        workspace_id=uuid4(),
    )

    assert returned is None
    session.execute.assert_awaited_once()
