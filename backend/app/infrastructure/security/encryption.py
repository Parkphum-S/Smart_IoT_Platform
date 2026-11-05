"""Authenticated encryption utilities for sensitive application data."""

import base64
import binascii
import re
import secrets
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_NONCE_SIZE = 12
_TAG_SIZE = 16
_AAD_PREFIX = b"smart-iot-platform:gateway-secret:v1:"


class EncryptionError(Exception):
    """Raised when encryption or decryption fails safely."""


def _encode_context(value: str, field_name: str) -> bytes:
    """Encode a context value unambiguously using a length prefix."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")

    encoded = value.encode("utf-8")

    if len(encoded) > 255:
        raise ValueError(f"{field_name} exceeds the maximum length.")

    return struct.pack(">I", len(encoded)) + encoded


def _build_aad(
    key_version: str,
    workspace_id: str,
    gateway_id: str,
) -> bytes:
    """Build authenticated context binding for a gateway secret."""
    if (
        not isinstance(key_version, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", key_version) is None
    ):
        raise ValueError("Invalid encryption key version.")

    return (
        _AAD_PREFIX
        + _encode_context(key_version, "key_version")
        + _encode_context(workspace_id, "workspace_id")
        + _encode_context(gateway_id, "gateway_id")
    )


class GatewaySecretEncryption:
    """Encrypt gateway secrets using AES-256-GCM with context binding."""

    def __init__(self, key: bytes, key_version: str) -> None:
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key.")

        if (
            not isinstance(key_version, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", key_version)
            is None
        ):
            raise ValueError("Invalid encryption key version.")

        self._cipher = AESGCM(key)
        self.key_version = key_version

    @classmethod
    def from_base64(
        cls,
        encoded_key: str,
        key_version: str,
    ) -> "GatewaySecretEncryption":
        """Create an encryption service from a Base64-encoded key."""
        try:
            key = base64.b64decode(encoded_key, validate=True)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise ValueError("Encryption key must be valid Base64.") from exc

        return cls(key=key, key_version=key_version)

    def encrypt(
        self,
        plaintext: str,
        *,
        workspace_id: str,
        gateway_id: str,
    ) -> str:
        """Encrypt plaintext bound to a specific workspace and gateway."""
        if not isinstance(plaintext, str) or not plaintext:
            raise ValueError("Plaintext must be a non-empty string.")

        aad = _build_aad(self.key_version, workspace_id, gateway_id)
        nonce = secrets.token_bytes(_NONCE_SIZE)

        encrypted = self._cipher.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            aad,
        )

        return base64.b64encode(nonce + encrypted).decode("ascii")

    def decrypt(
        self,
        encoded_ciphertext: str,
        key_version: str,
        *,
        workspace_id: str,
        gateway_id: str,
    ) -> str:
        """Authenticate context and decrypt a gateway secret."""
        if key_version != self.key_version:
            raise EncryptionError("Encryption key version does not match.")

        try:
            aad = _build_aad(key_version, workspace_id, gateway_id)
        except ValueError as exc:
            raise EncryptionError("Encryption context is invalid.") from exc

        try:
            payload = base64.b64decode(encoded_ciphertext, validate=True)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise EncryptionError("Ciphertext encoding is invalid.") from exc

        if len(payload) < _NONCE_SIZE + _TAG_SIZE:
            raise EncryptionError("Ciphertext is invalid or incomplete.")

        nonce = payload[:_NONCE_SIZE]
        ciphertext = payload[_NONCE_SIZE:]

        try:
            plaintext = self._cipher.decrypt(nonce, ciphertext, aad)
            return plaintext.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
            raise EncryptionError(
                "Ciphertext authentication or decryption failed."
            ) from exc

class GatewaySecretKeyring:
    """Manage versioned AES-256-GCM keys for gateway secrets."""

    def __init__(
        self,
        keys: dict[str, bytes],
        active_key_version: str,
    ) -> None:
        if not isinstance(keys, dict) or not keys:
            raise ValueError("At least one encryption key is required.")

        if active_key_version not in keys:
            raise ValueError("Active encryption key version is unavailable.")

        if any(not isinstance(key, bytes) or len(key) != 32
               for key in keys.values()):
            raise ValueError("Every key must be a 32-byte AES-256 key.")

        if len(set(keys.values())) != len(keys):
            raise ValueError(
                "Encryption key material must be unique across versions."
            )

        self._keys = {
            version: GatewaySecretEncryption(key, version)
            for version, key in keys.items()
        }
        self.active_key_version = active_key_version

    @classmethod
    def from_base64(
        cls,
        encoded_keys: dict[str, str],
        active_key_version: str,
    ) -> "GatewaySecretKeyring":
        """Build a keyring from Base64-encoded AES-256 keys."""
        if not isinstance(encoded_keys, dict) or not encoded_keys:
            raise ValueError("At least one encryption key is required.")

        decoded: dict[str, bytes] = {}
        for version, encoded_key in encoded_keys.items():
            try:
                decoded[version] = base64.b64decode(
                    encoded_key,
                    validate=True,
                )
            except (binascii.Error, ValueError, TypeError) as exc:
                raise ValueError(
                    "Encryption key must be valid Base64."
                ) from exc

        return cls(decoded, active_key_version)

    @property
    def key_version(self) -> str:
        """Return the active key version used for new encryption."""
        return self.active_key_version

    @property
    def key_versions(self) -> frozenset[str]:
        """Return configured key versions without exposing key material."""
        return frozenset(self._keys)

    def encrypt(
        self,
        plaintext: str,
        *,
        workspace_id: str,
        gateway_id: str,
    ) -> str:
        """Encrypt new data with the active key."""
        return self._keys[self.active_key_version].encrypt(
            plaintext,
            workspace_id=workspace_id,
            gateway_id=gateway_id,
        )

    def decrypt(
        self,
        encoded_ciphertext: str,
        key_version: str,
        *,
        workspace_id: str,
        gateway_id: str,
    ) -> str:
        """Decrypt data using the key matching its stored version."""
        encryption = self._keys.get(key_version)
        if encryption is None:
            raise EncryptionError("Encryption key version is unavailable.")

        return encryption.decrypt(
            encoded_ciphertext,
            key_version,
            workspace_id=workspace_id,
            gateway_id=gateway_id,
        )
