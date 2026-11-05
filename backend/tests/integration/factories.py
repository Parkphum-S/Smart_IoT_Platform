"""Factories for integration test database records."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, Workspace, WorkspaceMember
from app.modules.devices.models import Device, DeviceType


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


async def create_device_type(
    session: AsyncSession,
    *,
    name: str | None = None,
    description: str | None = None,
    capabilities: dict | None = None,
) -> DeviceType:
    """Create and flush a device type."""
    device_type = DeviceType(
        name=name or f"Integration Device Type {uuid4().hex[:12]}",
        description=description,
        capabilities=capabilities or {},
    )
    session.add(device_type)
    await session.flush()
    return device_type


async def create_device(
    session: AsyncSession,
    *,
    workspace: Workspace,
    device_type: DeviceType,
    device_uid: str | None = None,
    name: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
    protocol: str = "mqtt",
    lifecycle_status: str = "pending_provisioning",
    is_enabled: bool = True,
) -> Device:
    """Create and flush a device without invoking domain services."""
    device = Device(
        workspace_id=workspace.id,
        device_type_id=device_type.id,
        device_uid=device_uid or f"integration-device-{uuid4().hex}",
        name=name or f"Integration Device {uuid4().hex[:12]}",
        manufacturer=manufacturer,
        model=model,
        protocol=protocol,
        lifecycle_status=lifecycle_status,
        is_enabled=is_enabled,
    )
    session.add(device)
    await session.flush()
    return device
