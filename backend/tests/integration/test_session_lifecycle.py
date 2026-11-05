"""Integration tests for the user session lifecycle."""

from datetime import timedelta

from sqlalchemy import select

from app.core.session_tokens import hash_session_token
from app.modules.users.models import UserSession
from app.modules.users.services.session_service import SessionService
from factories import create_user


async def test_create_session_persists_hashed_token(db_session):
    """Create a session and verify only its token hash is stored."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    assert raw_token
    assert created.user_id == user.id
    assert created.token_hash == hash_session_token(raw_token)
    assert created.token_hash != raw_token
    assert created.revoked_at is None

    stored = await db_session.scalar(
        select(UserSession).where(UserSession.id == created.id)
    )
    assert stored is not None
    assert stored.token_hash == hash_session_token(raw_token)


async def test_validate_session_accepts_valid_token(db_session):
    """Accept a valid session belonging to an active user."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    validated = await service.validate_session(
        db_session,
        raw_token=raw_token,
    )

    assert validated is not None
    assert validated.id == created.id


async def test_validate_session_rejects_unknown_or_empty_token(db_session):
    """Reject tokens that do not identify a stored session."""
    service = SessionService()

    assert await service.validate_session(
        db_session,
        raw_token="unknown-integration-token",
    ) is None

    assert await service.validate_session(
        db_session,
        raw_token="",
    ) is None


async def test_validate_session_rejects_revoked_session(db_session):
    """Reject a session after it has been revoked."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    assert await service.revoke_session(
        db_session,
        raw_token=raw_token,
    ) is True

    await db_session.refresh(created)
    assert created.revoked_at is not None

    assert await service.validate_session(
        db_session,
        raw_token=raw_token,
    ) is None


async def test_validate_session_rejects_absolute_expiry(db_session):
    """Reject a session whose absolute expiry is in the past."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    # Keep the database expiry constraint valid while making the
    # absolute expiry earlier than the current time.
    created.created_at = created.created_at - timedelta(days=2)
    created.expires_at = created.created_at + timedelta(days=1)
    await db_session.flush()

    assert await service.validate_session(
        db_session,
        raw_token=raw_token,
    ) is None


async def test_validate_session_rejects_idle_timeout(db_session):
    """Reject a session that has been idle beyond the configured limit."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    created.last_seen_at = (
        service._utc_now()
        - timedelta(
            seconds=service.settings.session_idle_timeout_seconds + 10
        )
    )
    await db_session.flush()

    assert await service.validate_session(
        db_session,
        raw_token=raw_token,
    ) is None


async def test_validate_session_rejects_inactive_user(db_session):
    """Reject a valid session when its associated user is inactive."""
    user = await create_user(db_session, is_active=False)
    service = SessionService()

    raw_token, _ = await service.create_session(
        db_session,
        user_id=user.id,
    )

    assert await service.validate_session(
        db_session,
        raw_token=raw_token,
    ) is None


async def test_validate_session_updates_old_activity(db_session):
    """Update last_seen_at when the activity interval has elapsed."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    previous_last_seen = (
        service._utc_now()
        - timedelta(
            seconds=service.settings.session_activity_update_interval_seconds + 10
        )
    )
    created.last_seen_at = previous_last_seen
    await db_session.flush()

    validated = await service.validate_session(
        db_session,
        raw_token=raw_token,
    )

    assert validated is not None
    assert validated.last_seen_at > previous_last_seen

    await db_session.refresh(created)
    assert created.last_seen_at > previous_last_seen


async def test_revoke_session_is_idempotent(db_session):
    """Revoke one session and reject repeated revocation."""
    user = await create_user(db_session)
    service = SessionService()

    raw_token, created = await service.create_session(
        db_session,
        user_id=user.id,
    )

    assert await service.revoke_session(
        db_session,
        raw_token=raw_token,
    ) is True

    assert await service.revoke_session(
        db_session,
        raw_token=raw_token,
    ) is False

    await db_session.refresh(created)
    assert created.revoked_at is not None


async def test_revoke_all_user_sessions(db_session):
    """Revoke all active sessions without affecting another user."""
    user = await create_user(db_session)
    another_user = await create_user(db_session)
    service = SessionService()

    user_sessions = []
    user_tokens = []

    for _ in range(3):
        raw_token, created = await service.create_session(
            db_session,
            user_id=user.id,
        )
        user_tokens.append(raw_token)
        user_sessions.append(created)

    _, unrelated_session = await service.create_session(
        db_session,
        user_id=another_user.id,
    )

    assert await service.revoke_session(
        db_session,
        raw_token=user_tokens[0],
    ) is True

    revoked_count = await service.revoke_all_user_sessions(
        db_session,
        user_id=user.id,
    )

    assert revoked_count == 2

    for user_session in user_sessions:
        await db_session.refresh(user_session)
        assert user_session.revoked_at is not None

    await db_session.refresh(unrelated_session)
    assert unrelated_session.revoked_at is None
