import pytest

from app.modules.users.services.authorization.permissions import (
    Permission,
    WorkspaceRole,
)
from app.modules.users.services.authorization.policy import (
    ROLE_PERMISSIONS,
    get_role_permissions,
    has_permission,
)


EXPECTED_PERMISSIONS = {
    WorkspaceRole.OWNER: set(Permission),

    WorkspaceRole.ADMIN: set(Permission)
    - {
        Permission.WORKSPACE_DELETE,
        Permission.OWNERSHIP_TRANSFER,
    },

    WorkspaceRole.OPERATOR: {
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
    },

    WorkspaceRole.VIEWER: {
        Permission.WORKSPACE_READ,
        Permission.DEVICES_READ,
        Permission.ROOMS_READ,
        Permission.DEVICE_GROUPS_READ,
        Permission.TELEMETRY_READ,
        Permission.DEVICE_STATUS_READ,
        Permission.ALERTS_READ,
    },
}


@pytest.mark.parametrize("role", list(WorkspaceRole))
@pytest.mark.parametrize("permission", list(Permission))
def test_role_permission_matrix(role, permission):
    expected = permission in EXPECTED_PERMISSIONS[role]

    assert has_permission(role.value, permission.value) is expected


@pytest.mark.parametrize("role", list(WorkspaceRole))
def test_get_role_permissions_matches_approved_matrix(role):
    assert get_role_permissions(role.value) == frozenset(
        EXPECTED_PERMISSIONS[role]
    )


def test_permission_count_is_25():
    assert len(Permission) == 25


def test_all_four_roles_are_defined():
    assert len(WorkspaceRole) == 4


@pytest.mark.parametrize("unknown_role", ["", "superadmin", "member", None])
def test_unknown_role_has_no_permissions(unknown_role):
    assert get_role_permissions(unknown_role) == frozenset()


@pytest.mark.parametrize(
    "unknown_permission",
    ["", "workspace.superuser", "devices.admin", None],
)
def test_unknown_permission_is_denied(unknown_permission):
    assert has_permission("owner", unknown_permission) is False


def test_unknown_role_is_denied():
    assert has_permission("superadmin", "workspace.read") is False


def test_admin_cannot_delete_workspace():
    assert has_permission(
        "admin", Permission.WORKSPACE_DELETE.value
    ) is False


def test_admin_cannot_transfer_ownership():
    assert has_permission(
        "admin", Permission.OWNERSHIP_TRANSFER.value
    ) is False


def test_role_permission_mapping_is_immutable():
    with pytest.raises(TypeError):
        ROLE_PERMISSIONS[WorkspaceRole.VIEWER] = frozenset()
