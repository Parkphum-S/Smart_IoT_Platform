"""Factories for integration test database records."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, Workspace, WorkspaceMember


async def create_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    display_name: str = "Integration Test User",
    is_active: bool = True,
) -> User:
    """Create and flush a user with a unique email address."""
    user = User(
        email=email or f"integration-{uuid4().hex}@example.test",
        password_hash="integration-test-password-hash",
        display_name=display_name,
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def create_workspace(
    session: AsyncSession,
    *,
    name: str | None = None,
    description: str | None = None,
    timezone: str = "UTC",
) -> Workspace:
    """Create and flush a workspace."""
    workspace = Workspace(
        name=name or f"Integration Workspace {uuid4().hex[:12]}",
        description=description,
        timezone=timezone,
    )
    session.add(workspace)
    await session.flush()
    return workspace


async def create_membership(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    role: str = "viewer",
    is_active: bool = True,
) -> WorkspaceMember:
    """Create and flush a workspace membership."""
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
        is_active=is_active,
    )
    session.add(membership)
    await session.flush()
    return membership


async def create_workspace_with_owner(
    session: AsyncSession,
    *,
    owner: User | None = None,
    workspace_name: str | None = None,
) -> tuple[Workspace, User, WorkspaceMember]:
    """Create a workspace with one active owner."""
    if owner is None:
        owner = await create_user(
            session,
            display_name="Integration Workspace Owner",
        )

    workspace = await create_workspace(
        session,
        name=workspace_name,
    )

    membership = await create_membership(
        session,
        workspace=workspace,
        user=owner,
        role="owner",
    )

    return workspace, owner, membership
