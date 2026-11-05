"""Smoke tests for integration database fixtures and transaction isolation."""

from sqlalchemy import func, select, text

from app.modules.users.models import User
from factories import create_workspace_with_owner


async def test_database_connection_and_transaction_isolation(
    db_session,
    db_engine,
):
    """Verify the test database role and rollback-only transaction boundary."""
    identity = (
        await db_session.execute(
            text("SELECT current_database(), current_user")
        )
    ).one()

    assert identity.current_database == "smart_iot_integration_test"
    assert identity.current_user == "smart_iot_test_app"

    workspace, owner, membership = await create_workspace_with_owner(
        db_session
    )

    assert workspace.id is not None
    assert owner.id is not None
    assert membership.role == "owner"

    # A session commit must only release its savepoint, not commit the
    # outer transaction controlled by the fixture.
    await db_session.commit()

    visible_in_session = await db_session.scalar(
        select(User.id).where(User.id == owner.id)
    )
    assert visible_in_session == owner.id

    # A separate connection must not see the uncommitted outer transaction.
    async with db_engine.connect() as observer:
        visible_outside = await observer.scalar(
            select(func.count())
            .select_from(User)
            .where(User.id == owner.id)
        )

    assert visible_outside == 0
