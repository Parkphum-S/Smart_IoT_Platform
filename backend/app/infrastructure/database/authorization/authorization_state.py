"""Authorization lifecycle state and transition contract."""

from enum import StrEnum

from .authorization_errors import AuthorizationError


class AuthorizationState(StrEnum):
    ISSUED = "ISSUED"
    CLAIMED = "CLAIMED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    EXPIRED = "EXPIRED"


_ALLOWED_TRANSITIONS = {
    AuthorizationState.ISSUED: frozenset({
        AuthorizationState.CLAIMED,
        AuthorizationState.EXPIRED,
    }),
    AuthorizationState.CLAIMED: frozenset({
        AuthorizationState.EXECUTING,
        AuthorizationState.EXPIRED,
    }),
    AuthorizationState.EXECUTING: frozenset({
        AuthorizationState.SUCCEEDED,
        AuthorizationState.FAILED,
        AuthorizationState.UNKNOWN,
    }),
    AuthorizationState.UNKNOWN: frozenset({
        AuthorizationState.SUCCEEDED,
        AuthorizationState.FAILED,
    }),
    AuthorizationState.SUCCEEDED: frozenset(),
    AuthorizationState.FAILED: frozenset(),
    AuthorizationState.EXPIRED: frozenset(),
}


def allowed_transitions(
    state: AuthorizationState,
) -> frozenset[AuthorizationState]:
    """Return valid next states for the supplied state."""
    return _ALLOWED_TRANSITIONS[state]


def can_transition(
    current: AuthorizationState,
    target: AuthorizationState,
) -> bool:
    """Return whether a lifecycle transition is permitted."""
    return target in _ALLOWED_TRANSITIONS[current]


def validate_transition(
    current: AuthorizationState,
    target: AuthorizationState,
) -> None:
    """Raise an error when a lifecycle transition is invalid."""
    if not can_transition(current, target):
        raise InvalidAuthorizationTransition(
            f"Invalid authorization transition: "
            f"{current.value} -> {target.value}"
        )


class InvalidAuthorizationTransition(AuthorizationError):
    """Raised when an invalid authorization transition is requested."""
