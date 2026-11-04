"""Database repository for user sessions."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, UserSession


class UserSessionRepository:
    """Encapsulate database operations for user sessions."""

    @staticmethod
    async def create_session(
        session: AsyncSession,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UserSession:
        """Add a new session to the current transaction."""
        user_session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(user_session)
        await session.flush()
        return user_session

    @staticmethod
    async def get_session_by_token_hash(
        session: AsyncSession,
        token_hash: str,
    ) -> UserSession | None:
        """Find a session using its SHA-256 token hash."""
        statement = select(UserSession).where(
            UserSession.token_hash == token_hash
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_last_seen(
        session: AsyncSession,
        *,
        session_id: UUID,
        last_seen_at: datetime,
    ) -> bool:
        """Update activity time only for a non-revoked, unexpired session."""
        statement = (
            update(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > last_seen_at,
            )
            .values(last_seen_at=last_seen_at)
        )
        result = await session.execute(statement)
        return result.rowcount == 1

    @staticmethod
    async def revoke_session(
        session: AsyncSession,
        *,
        session_id: UUID,
        revoked_at: datetime,
    ) -> bool:
        """Revoke a session if it has not already been revoked."""
        statement = (
            update(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = await session.execute(statement)
        return result.rowcount == 1

    @staticmethod
    async def revoke_all_user_sessions(
        session: AsyncSession,
        *,
        user_id: UUID,
        revoked_at: datetime,
    ) -> int:
        """Revoke all active sessions belonging to a user."""
        statement = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = await session.execute(statement)
        return result.rowcount or 0


class UserRepository:
    """Encapsulate database operations for user accounts."""

    @staticmethod
    async def get_user_by_email(
        session: AsyncSession,
        email: str,
    ) -> User | None:
        """Find a user by email using case-insensitive matching."""
        normalized_email = email.strip().casefold()

        statement = select(User).where(
            func.lower(User.email) == normalized_email
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()
