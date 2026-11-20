"""Authorization domain and infrastructure error contract."""


class AuthorizationError(Exception):
    """Base class for authorization errors."""


class AuthorizationDeniedError(AuthorizationError):
    """Authorization policy explicitly denied the request."""


class AuthorizationConfigurationError(AuthorizationError):
    """Authorization configuration is invalid or incomplete."""


class AuthorizationNotFoundError(AuthorizationError):
    """Requested authorization state does not exist."""


class AuthorizationAlreadyClaimedError(AuthorizationError):
    """Authorization has already been claimed."""


class AuthorizationExpiredError(AuthorizationError):
    """Authorization capability has expired."""


class AuthorizationStateConflictError(AuthorizationError):
    """Requested state transition conflicts with persisted state."""


class AuthorizationConcurrencyError(AuthorizationError):
    """Concurrent authorization operation could not be completed."""


class AuthorizationIntegrityError(AuthorizationError):
    """Authorization data failed an integrity requirement."""


class AuthorizationPersistenceError(AuthorizationError):
    """Authorization state persistence operation failed."""


class AuthorizationExecutionError(AuthorizationError):
    """Migration execution failed or could not be confirmed."""


class AuthorizationRecoveryError(AuthorizationError):
    """Authorization recovery or reconciliation failed."""


class AuthorizationLockError(AuthorizationError):
    """Target execution lock could not be acquired or maintained."""
