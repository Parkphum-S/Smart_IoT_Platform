"""Domain exceptions for device management."""


class DeviceError(Exception):
    """Base exception for device-domain operations."""


class DeviceNotFound(DeviceError):
    """The requested device does not exist in the workspace."""


class DeviceTypeNotFound(DeviceError):
    """The requested global device type does not exist."""


class DevicePermissionDenied(DeviceError):
    """The actor lacks the required workspace permission."""


class DeviceInvalidInput(DeviceError):
    """The supplied device data is invalid."""


class DeviceStateConflict(DeviceError):
    """The requested operation conflicts with the current device state."""


class GatewayNotFound(DeviceError):
    """The requested gateway does not exist."""


class GatewayAlreadyRegistered(DeviceError):
    """The device is already registered as a gateway."""


class GatewayMembershipConflict(DeviceError):
    """The requested gateway membership conflicts with existing state."""


class GatewayCycleDetected(DeviceError):
    """The requested gateway assignment would create a cycle."""


class GatewaySecretAlreadyExists(DeviceError):
    """A secret with the same name already exists for this gateway."""


class GatewaySecretNotFound(DeviceError):
    """The requested gateway secret does not exist."""


class GatewaySecretEncryptionUnavailable(DeviceError):
    """Gateway secret encryption is not configured."""
