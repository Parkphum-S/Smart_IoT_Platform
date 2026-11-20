"""Resolve Ed25519 public keys from an explicitly trusted local registry."""

from __future__ import annotations

import base64
import binascii
import re
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import StrictStr, field_validator, model_validator

from .trusted_manifest import StrictManifestModel


_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PUBLIC_KEY_SIZE = 32


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 timestamp requiring an explicit timezone."""
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("invalid key validity timestamp")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("key validity timestamp must be ISO 8601") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("key validity timestamp must include timezone")

    return parsed


class TrustedKeyError(ValueError):
    """Raised when a trusted public key cannot be resolved."""


class TrustedPublicKeyRecord(StrictManifestModel):
    """One key record supplied by a separately trusted registry."""

    key_id: StrictStr
    algorithm: Literal["Ed25519"]
    status: Literal["active", "revoked"]
    public_key: StrictStr
    not_before: StrictStr
    not_after: StrictStr

    @field_validator("not_before", "not_after")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        _parse_timestamp(value)
        return value

    @field_validator("key_id")
    @classmethod
    def validate_key_id(cls, value: str) -> str:
        if not _KEY_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid trusted key_id")
        return value

    @field_validator("public_key")
    @classmethod
    def validate_public_key_encoding(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("public key must be valid Base64") from exc

        if len(decoded) != _PUBLIC_KEY_SIZE:
            raise ValueError("invalid Ed25519 public key length")

        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("public key Base64 must be canonical")

        return value

    @model_validator(mode="after")
    def validate_validity_window(self) -> "TrustedPublicKeyRecord":
        not_before = _parse_timestamp(self.not_before)
        not_after = _parse_timestamp(self.not_after)

        if not_after <= not_before:
            raise ValueError("key not_after must follow not_before")

        return self


def resolve_trusted_public_key(
    key_id: str,
    registry: Iterable[TrustedPublicKeyRecord | dict],
    *,
    now: datetime | None = None,
) -> bytes:
    """Resolve an exact key ID and enforce registry status and validity.

    The registry must come from an independently trusted local source.
    This function deliberately does not load files or derive paths from key_id.
    """
    if type(key_id) is not str or not _KEY_ID_PATTERN.fullmatch(key_id):
        raise TrustedKeyError("invalid requested key_id")

    if now is None:
        now = datetime.now(timezone.utc)

    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        raise TrustedKeyError("resolution time must be timezone-aware")

    try:
        records = list(registry)
    except Exception as exc:
        raise TrustedKeyError("trusted key registry is invalid") from exc

    matches: list[TrustedPublicKeyRecord] = []
    seen: set[str] = set()

    try:
        for item in records:
            if isinstance(item, TrustedPublicKeyRecord):
                record = item
            elif isinstance(item, dict):
                record = TrustedPublicKeyRecord.model_validate(item)
            else:
                raise TrustedKeyError("invalid trusted key registry entry")

            if record.key_id in seen:
                raise TrustedKeyError("duplicate key_id in trusted registry")
            seen.add(record.key_id)

            if record.key_id == key_id:
                matches.append(record)
    except TrustedKeyError:
        raise
    except Exception as exc:
        raise TrustedKeyError("trusted key registry validation failed") from exc

    if len(matches) != 1:
        raise TrustedKeyError("trusted key_id not found")

    record = matches[0]

    if record.status != "active":
        raise TrustedKeyError("trusted key is revoked")

    not_before = _parse_timestamp(record.not_before)
    not_after = _parse_timestamp(record.not_after)

    if now < not_before:
        raise TrustedKeyError("trusted key is not yet valid")

    if now >= not_after:
        raise TrustedKeyError("trusted key has expired")

    try:
        public_key = base64.b64decode(
            record.public_key,
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise TrustedKeyError("trusted public key decoding failed") from exc

    if len(public_key) != _PUBLIC_KEY_SIZE:
        raise TrustedKeyError("invalid Ed25519 public key length")

    return public_key
