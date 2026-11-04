"""Centralized role and permission identifiers for workspace authorization."""

from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(StrEnum):
    # Workspace
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_UPDATE = "workspace.update"
    WORKSPACE_DELETE = "workspace.delete"

    # Members
    MEMBERS_READ = "members.read"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_UPDATE = "members.update"
    MEMBERS_DEACTIVATE = "members.deactivate"
    MEMBERS_ROLE_ASSIGN = "members.role.assign"

    # Ownership
    OWNERSHIP_TRANSFER = "ownership.transfer"

    # Devices
    DEVICES_READ = "devices.read"
    DEVICES_CREATE = "devices.create"
    DEVICES_UPDATE = "devices.update"
    DEVICES_DELETE = "devices.delete"
    DEVICES_CONTROL = "devices.control"

    # Rooms and device groups
    ROOMS_READ = "rooms.read"
    ROOMS_MANAGE = "rooms.manage"
    DEVICE_GROUPS_READ = "device_groups.read"
    DEVICE_GROUPS_MANAGE = "device_groups.manage"

    # Telemetry and device status
    TELEMETRY_READ = "telemetry.read"
    DEVICE_STATUS_READ = "device_status.read"

    # Alerts
    ALERTS_READ = "alerts.read"
    ALERTS_MANAGE = "alerts.manage"

    # Automation
    AUTOMATION_READ = "automation.read"
    AUTOMATION_MANAGE = "automation.manage"

    # Audit
    AUDIT_READ = "audit.read"
