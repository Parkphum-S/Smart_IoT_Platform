"""Database access for workspace authorization."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, WorkspaceMember


class AuthorizationRepository:
    """Read active workspace membership for authorization checks."""

    @staticmethod
    async def get_active_membership(
        session: AsyncSession,
        *,
        user_id: UUID,
        workspace_id: UUID,
    ) -> WorkspaceMember | None:
        """Return active membership only when the associated user is active."""
        statement = (
            select(WorkspaceMember)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_active.is_(True),
                User.is_active.is_(True),
            )
        )

        result = await session.execute(statement)
        return result.scalar_one_or_none()
