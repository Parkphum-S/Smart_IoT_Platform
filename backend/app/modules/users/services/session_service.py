"""Business logic for user session lifecycle management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.session_tokens import generate_session_token, hash_session_token
from app.modules.users.models import User, UserSession
from app.modules.users.repository import UserSessionRepository


class SessionService:
    """Manage secure user sessions using PostgreSQL as the session store."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.repository = UserSessionRepository()

    @staticmethod
    def _utc_now() -> datetime:
        """Return the current timezone-aware UTC timestamp."""
        return datetime.now(timezone.utc)

    async def create_session(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
    ) -> tuple[str, UserSession]:
        """Create a session and return its raw token for cookie delivery."""
        now = self._utc_now()
        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)

        user_session = await self.repository.create_session(
            session,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=now + timedelta(
                seconds=self.settings.session_absolute_lifetime_seconds
            ),
        )

        return raw_token, user_session

    async def validate_session(
        self,
        session: AsyncSession,
        *,
        raw_token: str,
    ) -> UserSession | None:
        """Validate token, session lifetime, and associated user status."""
        if not raw_token:
            return None

        now = self._utc_now()
        token_hash = hash_session_token(raw_token)

        user_session = await self.repository.get_session_by_token_hash(
            session,
            token_hash,
        )

        if user_session is None:
            return None

        if user_session.revoked_at is not None:
            return None

        idle_timeout = timedelta(
            seconds=self.settings.session_idle_timeout_seconds
        )

        if user_session.expires_at <= now:
            return None

        if user_session.last_seen_at + idle_timeout <= now:
            return None

        user_statement = select(User.is_active).where(
            User.id == user_session.user_id
        )
        user_result = await session.execute(user_statement)
        is_user_active = user_result.scalar_one_or_none()

        if is_user_active is not True:
            return None

        activity_interval = timedelta(
            seconds=self.settings.session_activity_update_interval_seconds
        )

        if user_session.last_seen_at + activity_interval <= now:
            updated = await self.repository.update_last_seen(
                session,
                session_id=user_session.id,
                last_seen_at=now,
            )

            if not updated:
                return None

            user_session.last_seen_at = now

        return user_session

    async def revoke_session(
        self,
        session: AsyncSession,
        *,
        raw_token: str,
    ) -> bool:
        """Revoke the session associated with a raw token."""
        if not raw_token:
            return False

        token_hash = hash_session_token(raw_token)

        user_session = await self.repository.get_session_by_token_hash(
            session,
            token_hash,
        )

        if user_session is None:
            return False

        return await self.repository.revoke_session(
            session,
            session_id=user_session.id,
            revoked_at=self._utc_now(),
        )

    async def revoke_all_user_sessions(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
    ) -> int:
        """Revoke all active sessions belonging to a user."""
        return await self.repository.revoke_all_user_sessions(
            session,
            user_id=user_id,
            revoked_at=self._utc_now(),
        )
