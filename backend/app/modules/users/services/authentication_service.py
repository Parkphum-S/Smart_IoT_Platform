"""Business logic for user authentication."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, needs_rehash, verify_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class AuthenticationService:
    """Authenticate users with Argon2id password verification."""

    def __init__(self) -> None:
        self.repository = UserRepository()

    async def authenticate(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> User | None:
        """Return an active user when the supplied credentials are valid."""
        user = await self.repository.get_user_by_email(session, email)

        if user is None:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await session.flush()

        return user
