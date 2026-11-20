"""Strict descriptor binding one trusted bundle generation to raw file digests."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import StrictStr, field_validator

from .trusted_manifest import StrictManifestModel


_GENERATION_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
)
_KEY_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TrustedBundleDescriptor(StrictManifestModel):
    """Immutable integrity descriptor for one bundle generation."""

    schema_version: Literal[1]
    generation_id: StrictStr
    manifest_sha256: StrictStr
    signature_sha256: StrictStr
    registry_sha256: StrictStr
    selected_key_id: StrictStr
    created_at: datetime

    @field_validator("generation_id")
    @classmethod
    def validate_generation_id(cls, value: str) -> str:
        if _GENERATION_PATTERN.fullmatch(value) is None:
            raise ValueError("invalid bundle generation ID")
        return value

    @field_validator(
        "manifest_sha256",
        "signature_sha256",
        "registry_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _DIGEST_PATTERN.fullmatch(value) is None:
            raise ValueError("invalid SHA-256 digest")
        return value

    @field_validator("selected_key_id")
    @classmethod
    def validate_key_id(cls, value: str) -> str:
        if _KEY_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("invalid selected key ID")
        return value

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: object) -> datetime:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ValueError(
                    "descriptor timestamp must be valid ISO-8601"
                ) from exc

        if not isinstance(value, datetime):
            raise ValueError("descriptor timestamp must be a datetime")

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("descriptor timestamp must be timezone-aware")

        return value.astimezone(timezone.utc)
