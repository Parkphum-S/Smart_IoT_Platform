from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.users.services.membership.repository import (
    MembershipRepository,
)


def compile_statement(session):
    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    return str(compiled).lower(), compiled.params


@pytest.mark.asyncio
async def test_get_workspace_for_update_uses_transaction_advisory_lock():
    workspace_id = uuid4()
    workspace = Mock()
    lock_result = Mock()
    workspace_result = Mock()
    workspace_result.scalar_one_or_none.return_value = workspace

    session = Mock()
    session.execute = AsyncMock(
        side_effect=[lock_result, workspace_result]
    )

    returned = await MembershipRepository.get_workspace_for_update(
        session,
        workspace_id=workspace_id,
    )

    assert returned is workspace
    assert session.execute.await_count == 2

    lock_statement = session.execute.await_args_list[0].args[0]
    lock_compiled_statement = lock_statement.compile(
        dialect=postgresql.dialect()
    )
    lock_compiled = str(lock_compiled_statement).lower()

    assert "pg_advisory_xact_lock" in lock_compiled
    assert "hashtextextended" in lock_compiled
    assert str(workspace_id) in lock_compiled_statement.params.values()

    workspace_statement = session.execute.await_args_list[1].args[0]
    workspace_compiled = str(
        workspace_statement.compile(dialect=postgresql.dialect())
    ).lower()
    workspace_params = workspace_statement.compile(
        dialect=postgresql.dialect()
    ).params

    assert "from workspaces" in workspace_compiled
    assert "for update" not in workspace_compiled
    assert workspace_id in workspace_params.values()


@pytest.mark.asyncio
async def test_get_active_user_filters_inactive_accounts():
    user_id = uuid4()
    result = Mock()
    result.scalar_one_or_none.return_value = None

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await MembershipRepository.get_active_user(
        session,
        user_id=user_id,
    )

    sql, params = compile_statement(session)

    assert returned is None
    assert "from users" in sql
    assert "users.is_active is true" in sql
    assert user_id in params.values()


@pytest.mark.asyncio
async def test_get_membership_by_user_scopes_workspace_and_user():
    workspace_id = uuid4()
    user_id = uuid4()
    membership = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = membership

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await MembershipRepository.get_membership_by_user(
        session,
        workspace_id=workspace_id,
        user_id=user_id,
    )

    sql, params = compile_statement(session)

    assert returned is membership
    assert "workspace_members.workspace_id =" in sql
    assert "workspace_members.user_id =" in sql
    assert "for update" not in sql
    assert workspace_id in params.values()
    assert user_id in params.values()


@pytest.mark.asyncio
async def test_get_membership_by_user_can_lock_row():
    result = Mock()
    result.scalar_one_or_none.return_value = None

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    await MembershipRepository.get_membership_by_user(
        session,
        workspace_id=uuid4(),
        user_id=uuid4(),
        for_update=True,
    )

    sql, _ = compile_statement(session)
    assert "for update" in sql


@pytest.mark.asyncio
async def test_get_membership_for_update_scopes_and_locks_target():
    workspace_id = uuid4()
    membership_id = uuid4()
    membership = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = membership

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await MembershipRepository.get_membership_for_update(
        session,
        workspace_id=workspace_id,
        membership_id=membership_id,
    )

    sql, params = compile_statement(session)

    assert returned is membership
    assert "workspace_members.workspace_id =" in sql
    assert "workspace_members.id =" in sql
    assert "for update" in sql
    assert workspace_id in params.values()
    assert membership_id in params.values()


@pytest.mark.asyncio
async def test_list_memberships_excludes_inactive_by_default():
    workspace_id = uuid4()
    members = [Mock(), Mock()]
    result = Mock()
    result.scalars.return_value.all.return_value = members

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await MembershipRepository.list_memberships(
        session,
        workspace_id=workspace_id,
    )

    sql, params = compile_statement(session)

    assert returned == members
    assert "workspace_members.workspace_id =" in sql
    assert "workspace_members.is_active is true" in sql
    assert "order by" in sql
    assert workspace_id in params.values()


@pytest.mark.asyncio
async def test_list_memberships_can_include_inactive():
    result = Mock()
    result.scalars.return_value.all.return_value = []

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    await MembershipRepository.list_memberships(
        session,
        workspace_id=uuid4(),
        include_inactive=True,
    )

    sql, _ = compile_statement(session)
    assert "workspace_members.is_active is true" not in sql


@pytest.mark.asyncio
async def test_get_latest_deactivation_orders_and_limits_history():
    membership_id = uuid4()
    history = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = history

    session = Mock()
    session.execute = AsyncMock(return_value=result)

    returned = await MembershipRepository.get_latest_deactivation(
        session,
        membership_id=membership_id,
    )

    sql, params = compile_statement(session)

    assert returned is history
    assert "from membership_history" in sql
    assert "membership_history.event_type =" in sql
    assert "membership_history.membership_id =" in sql
    assert "order by membership_history.event_sequence desc" in sql
    assert "membership_history.created_at desc" not in sql
    assert "limit" in sql
    assert membership_id in params.values()


@pytest.mark.asyncio
async def test_add_membership_history_flushes_without_commit():
    session = Mock()
    session.flush = AsyncMock()

    workspace_id = uuid4()
    membership_id = uuid4()
    actor_id = uuid4()
    subject_user_id = uuid4()

    history = await MembershipRepository.add_membership_history(
        session,
        workspace_id=workspace_id,
        membership_id=membership_id,
        actor_id=actor_id,
        subject_user_id=subject_user_id,
        event_type="role_changed",
        previous_role="viewer",
        new_role="operator",
        details={"source": "test"},
    )

    assert history.workspace_id == workspace_id
    assert history.membership_id == membership_id
    assert history.actor_id == actor_id
    assert history.subject_user_id == subject_user_id
    assert history.event_type == "role_changed"
    assert history.previous_role == "viewer"
    assert history.new_role == "operator"
    assert history.details == {"source": "test"}
    session.add.assert_called_once_with(history)
    session.flush.assert_awaited_once()
    assert not hasattr(session, "commit") or not session.commit.called


@pytest.mark.asyncio
async def test_add_audit_log_flushes_without_commit():
    session = Mock()
    session.flush = AsyncMock()

    workspace_id = uuid4()
    actor_id = uuid4()
    resource_id = uuid4()

    audit = await MembershipRepository.add_audit_log(
        session,
        workspace_id=workspace_id,
        actor_id=actor_id,
        action="membership.role_changed",
        resource_type="workspace_member",
        resource_id=resource_id,
        details={"old_role": "viewer", "new_role": "operator"},
    )

    assert audit.workspace_id == workspace_id
    assert audit.actor_type == "user"
    assert audit.actor_id == actor_id
    assert audit.action == "membership.role_changed"
    assert audit.resource_type == "workspace_member"
    assert audit.resource_id == resource_id
    assert audit.details == {"old_role": "viewer", "new_role": "operator"}
    session.add.assert_called_once_with(audit)
    session.flush.assert_awaited_once()
    assert not hasattr(session, "commit") or not session.commit.called


@pytest.mark.asyncio
async def test_add_system_audit_log_uses_system_actor_type():
    session = Mock()
    session.flush = AsyncMock()

    audit = await MembershipRepository.add_audit_log(
        session,
        workspace_id=uuid4(),
        actor_id=None,
        action="membership.system_action",
        resource_type="workspace_member",
        resource_id=None,
    )

    assert audit.actor_type == "system"
    assert audit.actor_id is None
    assert audit.details == {}
    session.flush.assert_awaited_once()
