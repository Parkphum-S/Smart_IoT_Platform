"""Integration tests for PostgreSQL append-only and owner invariants."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.infrastructure.database.session import create_database_engine

from app.modules.monitoring.models import AuditLog
from app.modules.users.models import MembershipHistory
from factories import create_workspace_with_owner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("table", "operation"),
    [
        ("membership_history", "UPDATE"),
        ("membership_history", "DELETE"),
        ("audit_logs", "UPDATE"),
        ("audit_logs", "DELETE"),
    ],
)
async def test_permanent_records_reject_mutation(db_session, table, operation):
    workspace, owner, membership = await create_workspace_with_owner(db_session)

    if table == "membership_history":
        history = MembershipHistory(
            workspace_id=workspace.id,
            membership_id=membership.id,
            actor_id=owner.id,
            subject_user_id=owner.id,
            event_type="created",
            previous_role=None,
            new_role="owner",
            details={},
        )
        db_session.add(history)
        await db_session.flush()

        record_id = history.event_sequence
        key_column = "event_sequence"
    else:
        audit = AuditLog(
            workspace_id=workspace.id,
            actor_type="user",
            actor_id=owner.id,
            action="integration.test",
            resource_type="workspace",
            resource_id=workspace.id,
            details={},
        )
        db_session.add(audit)
        await db_session.flush()

        record_id = audit.id
        key_column = "id"

    if operation == "UPDATE":
        statement = text(
            f"UPDATE {table} SET details = '{{}}' "
            f"WHERE {key_column} = :record_id"
        )
    else:
        statement = text(
            f"DELETE FROM {table} "
            f"WHERE {key_column} = :record_id"
        )

    with pytest.raises(DBAPIError) as exc_info:
        async with db_session.begin_nested():
            await db_session.execute(
                statement,
                {"record_id": record_id},
            )

    assert getattr(exc_info.value.orig, "sqlstate", None) == "55000"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "table",
    ["membership_history", "audit_logs"],
)
async def test_permanent_records_reject_truncate(table):
    settings = get_settings()

    assert settings.app_env == "testing"
    assert settings.migration_database_url is not None
    assert settings.migration_database_role == "smart_iot_test_owner"

    engine = create_database_engine(
        str(settings.migration_database_url),
    )

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()

            try:
                identity = (
                    await connection.execute(
                        text("SELECT session_user, current_user")
                    )
                ).one()

                assert identity[0] == "smart_iot_test_migrator"

                await connection.execute(
                    text("SET LOCAL ROLE smart_iot_test_owner")
                )

                current_role = (
                    await connection.execute(
                        text("SELECT current_user")
                    )
                ).scalar_one()

                assert current_role == "smart_iot_test_owner"

                with pytest.raises(DBAPIError) as exc_info:
                    async with connection.begin_nested():
                        await connection.execute(
                            text(f"TRUNCATE TABLE {table}")
                        )

                assert (
                    getattr(exc_info.value.orig, "sqlstate", None)
                    == "55000"
                )

            finally:
                if transaction.is_active:
                    await transaction.rollback()

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_database_rejects_removing_last_active_owner(db_session):
    workspace, _, membership = await create_workspace_with_owner(db_session)

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("""
                    UPDATE workspace_members
                    SET is_active = FALSE
                    WHERE id = :membership_id
                """),
                {"membership_id": membership.id},
            )

            await db_session.execute(
                text(
                    "SET CONSTRAINTS "
                    "trg_workspace_members_active_owner IMMEDIATE"
                )
            )


@pytest.mark.asyncio
async def test_database_rejects_moving_membership_between_workspaces(db_session):
    workspace, _, membership = await create_workspace_with_owner(db_session)
    other_workspace, _, _ = await create_workspace_with_owner(db_session)

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("""
                    UPDATE workspace_members
                    SET workspace_id = :new_workspace_id
                    WHERE id = :membership_id
                """),
                {
                    "new_workspace_id": other_workspace.id,
                    "membership_id": membership.id,
                },
            )
