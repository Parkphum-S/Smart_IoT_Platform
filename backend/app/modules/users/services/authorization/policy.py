"""Centralized, explicit workspace role-to-permission policy."""

from types import MappingProxyType

from app.modules.users.services.authorization.permissions import (
    Permission,
    WorkspaceRole,
)


ROLE_PERMISSIONS = MappingProxyType(
    {
        WorkspaceRole.OWNER: frozenset(Permission),

        WorkspaceRole.ADMIN: frozenset(
            permission
            for permission in Permission
            if permission
            not in {
                Permission.WORKSPACE_DELETE,
                Permission.OWNERSHIP_TRANSFER,
            }
        ),

        WorkspaceRole.OPERATOR: frozenset(
            {
                Permission.WORKSPACE_READ,
                Permission.DEVICES_READ,
                Permission.DEVICES_CONTROL,
                Permission.ROOMS_READ,
                Permission.DEVICE_GROUPS_READ,
                Permission.TELEMETRY_READ,
                Permission.DEVICE_STATUS_READ,
                Permission.ALERTS_READ,
                Permission.ALERTS_MANAGE,
                Permission.AUTOMATION_READ,
                Permission.AUTOMATION_MANAGE,
            }
        ),

        WorkspaceRole.VIEWER: frozenset(
            {
                Permission.WORKSPACE_READ,
                Permission.DEVICES_READ,
                Permission.ROOMS_READ,
                Permission.DEVICE_GROUPS_READ,
                Permission.TELEMETRY_READ,
                Permission.DEVICE_STATUS_READ,
                Permission.ALERTS_READ,
            }
        ),
    }
)


def get_role_permissions(role: str) -> frozenset[Permission]:
    """Return the explicit permissions for a role; unknown roles get none."""
    try:
        normalized_role = WorkspaceRole(role)
    except (TypeError, ValueError):
        return frozenset()

    return ROLE_PERMISSIONS.get(normalized_role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    """Check a permission using deny-by-default behavior."""
    try:
        normalized_permission = Permission(permission)
    except (TypeError, ValueError):
        return False

    return normalized_permission in get_role_permissions(role)
