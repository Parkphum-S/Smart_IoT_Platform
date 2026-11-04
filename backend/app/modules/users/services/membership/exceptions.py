"""Business exceptions for workspace membership management."""


class MembershipError(Exception):
    """Base exception for membership business rules."""


class WorkspaceNotFound(MembershipError):
    """The requested workspace does not exist."""


class MembershipNotFound(MembershipError):
    """The requested membership does not exist in the workspace."""


class UserNotFoundOrInactive(MembershipError):
    """The requested platform user does not exist or is inactive."""


class MembershipAlreadyExists(MembershipError):
    """A membership already exists, including an inactive membership."""


class MembershipInactive(MembershipError):
    """The requested membership is inactive."""


class MembershipAlreadyActive(MembershipError):
    """The requested membership is already active."""


class MembershipPermissionDenied(MembershipError):
    """The actor lacks permission for the requested membership operation."""


class InvalidRoleAssignment(MembershipError):
    """The actor cannot assign the requested role."""


class SelfManagementProhibited(MembershipError):
    """An actor cannot manage their own membership through these workflows."""


class OwnerDeactivationProhibited(MembershipError):
    """The active workspace owner cannot be deactivated."""


class OwnershipTransferRequired(MembershipError):
    """The owner must transfer ownership before leaving the workspace."""


class InvalidOwnershipTransferTarget(MembershipError):
    """The ownership transfer target is not an eligible active member."""


class DeactivationHistoryNotFound(MembershipError):
    """No valid deactivation history exists to restore the previous role."""
