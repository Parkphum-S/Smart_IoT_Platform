"""Reusable FastAPI dependencies for database and authorization."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.security import SESSION_COOKIE_NAME
from app.core.config import Settings, get_settings
from app.modules.users.models import User, WorkspaceMember
from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.session_service import SessionService


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide a database session and transaction for one API request."""
    session_factory = request.app.state.db_session_factory

    async with session_factory() as session:
        async with session.begin():
            yield session


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Return the active user associated with a valid session cookie."""
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    session_service = SessionService(settings)
    user_session = await session_service.validate_session(
        session,
        raw_token=raw_token,
    )

    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        )

    result = await session.execute(
        select(User).where(User.id == user_session.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return user


def require_permission(permission: str):
    """Create a dependency that requires a permission in the route workspace."""

    async def permission_dependency(
        workspace_id: UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> WorkspaceMember:
        authorization_service = AuthorizationService()

        try:
            return await authorization_service.authorize(
                session,
                user_id=current_user.id,
                workspace_id=workspace_id,
                permission=permission,
            )
        except WorkspaceMembershipNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            ) from None
        except PermissionDenied:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            ) from None

    return permission_dependency
