"""RFC 8785 and Ed25519 manifest signature verification."""

from __future__ import annotations

import base64
import binascii
import re
from typing import Literal

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)
from pydantic import StrictStr, field_validator

from .trusted_manifest import StrictManifestModel


_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_ED25519_PUBLIC_KEY_SIZE = 32
_ED25519_SIGNATURE_SIZE = 64


class ManifestSignatureError(ValueError):
    """Raised when a manifest signature cannot be trusted."""


class ManifestSignatureEnvelope(StrictManifestModel):
    key_id: StrictStr
    algorithm: Literal["Ed25519"]
    signature: StrictStr

    @field_validator("key_id")
    @classmethod
    def validate_key_id(cls, value: str) -> str:
        if not _KEY_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid signature key_id")
        return value

    @field_validator("signature")
    @classmethod
    def validate_signature_encoding(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("signature must be valid Base64") from exc

        if len(decoded) != _ED25519_SIGNATURE_SIZE:
            raise ValueError("invalid Ed25519 signature length")

        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("signature Base64 must be canonical")

        return value


def canonicalize_manifest_payload(payload: object) -> bytes:
    """Return RFC 8785 canonical JSON bytes for a JSON object payload."""
    if not isinstance(payload, dict):
        raise ManifestSignatureError(
            "manifest payload must be a JSON object"
        )

    try:
        return rfc8785.dumps(payload)
    except (rfc8785.CanonicalizationError, TypeError, ValueError) as exc:
        raise ManifestSignatureError(
            "manifest payload cannot be canonicalized"
        ) from exc


def verify_manifest_signature(
    payload: object,
    envelope: ManifestSignatureEnvelope | dict,
    trusted_public_key: bytes,
) -> bool:
    """Verify using a public key supplied by an external trusted resolver."""
    try:
        if isinstance(envelope, dict):
            envelope = ManifestSignatureEnvelope.model_validate(envelope)
        elif not isinstance(envelope, ManifestSignatureEnvelope):
            raise ManifestSignatureError(
                "invalid signature envelope type"
            )
    except ManifestSignatureError:
        raise
    except Exception as exc:
        raise ManifestSignatureError(
            "invalid signature envelope"
        ) from exc

    if type(trusted_public_key) is not bytes:
        raise ManifestSignatureError(
            "trusted public key must be raw bytes"
        )

    if len(trusted_public_key) != _ED25519_PUBLIC_KEY_SIZE:
        raise ManifestSignatureError(
            "invalid Ed25519 public key length"
        )

    try:
        signature = base64.b64decode(
            envelope.signature,
            validate=True,
        )
        public_key = Ed25519PublicKey.from_public_bytes(
            trusted_public_key
        )
        canonical_payload = canonicalize_manifest_payload(payload)
        public_key.verify(signature, canonical_payload)
    except InvalidSignature as exc:
        raise ManifestSignatureError(
            "manifest signature verification failed"
        ) from exc
    except ManifestSignatureError:
        raise
    except Exception as exc:
        raise ManifestSignatureError(
            "manifest signature verification could not complete"
        ) from exc

    return True
