"""Verified trusted manifest provider.

A VerifiedManifest represents a manifest whose validity, trusted key
status, and Ed25519 signature have been checked by this provider.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import StrictStr, field_validator

from .manifest_bundle import (
    TrustedManifestBundle,
)
from .manifest_signature import (
    ManifestSignatureError,
    canonicalize_manifest_payload,
    verify_manifest_signature,
)
from .trusted_key_store import (
    TrustedKeyError,
    resolve_trusted_public_key,
)
from .trusted_manifest import (
    StrictManifestModel,
    TrustedManifestPayload,
    validate_manifest_payload,
)


_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class VerifiedManifestError(ValueError):
    """Raised when a trusted manifest cannot be verified."""


class VerifiedManifest(StrictManifestModel):
    """Immutable result of successful manifest verification."""

    manifest: TrustedManifestPayload
    key_id: StrictStr
    algorithm: Literal["Ed25519"]
    manifest_digest: StrictStr
    verified_at: datetime

    @field_validator("manifest_digest")
    @classmethod
    def validate_manifest_digest(cls, value: str) -> str:
        if not _DIGEST_PATTERN.fullmatch(value):
            raise ValueError("invalid manifest SHA-256 digest")
        return value

    @field_validator("verified_at")
    @classmethod
    def validate_verified_at(cls, value: datetime) -> datetime:
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError("verified_at must be timezone-aware")

        return value.astimezone(timezone.utc)


def verify_trusted_manifest_bundle(
    bundle: TrustedManifestBundle,
    *,
    now: datetime | None = None,
) -> VerifiedManifest:
    """Validate and cryptographically verify a trusted manifest bundle.

    The bundle must originate from the trusted local bundle loader.
    No file access, database access, or external key lookup is performed.
    """

    if not isinstance(bundle, TrustedManifestBundle):
        raise VerifiedManifestError(
            "invalid trusted manifest bundle type"
        )

    if now is None:
        effective_now = datetime.now(timezone.utc)
    elif (
        isinstance(now, datetime)
        and now.tzinfo is not None
        and now.utcoffset() is not None
    ):
        effective_now = now.astimezone(timezone.utc)
    else:
        raise VerifiedManifestError(
            "verification time must be timezone-aware"
        )

    try:
        # Revalidate the manifest validity window at verification time.
        payload = bundle.manifest.model_dump(mode="json")

        manifest = validate_manifest_payload(
            payload,
            now=effective_now,
        )

        # Bind the signed envelope to the explicitly selected key.
        if bundle.signature.key_id != bundle.selected_key_id:
            raise VerifiedManifestError(
                "signature key_id does not match selected key_id"
            )

        # Resolve only from the immutable registry snapshot in this bundle.
        public_key = resolve_trusted_public_key(
            bundle.selected_key_id,
            bundle.key_registry,
            now=effective_now,
        )

        # Use the validated manifest representation consistently.
        payload = manifest.model_dump(mode="json")

        # The existing verifier canonicalizes this same JSON payload
        # internally using RFC 8785.
        signature_valid = verify_manifest_signature(
            payload,
            bundle.signature,
            public_key,
        )

        if signature_valid is not True:
            raise VerifiedManifestError(
                "manifest signature verification did not succeed"
            )

        # Digest the RFC 8785 bytes corresponding to the verified payload.
        canonical_payload = canonicalize_manifest_payload(payload)

        manifest_digest = hashlib.sha256(
            canonical_payload
        ).hexdigest()

        # Construct the result only after all checks have succeeded.
        return VerifiedManifest(
            manifest=manifest,
            key_id=bundle.signature.key_id,
            algorithm=bundle.signature.algorithm,
            manifest_digest=manifest_digest,
            verified_at=effective_now,
        )

    except VerifiedManifestError:
        raise
    except (
        ManifestSignatureError,
        TrustedKeyError,
        ValueError,
        TypeError,
    ) as exc:
        raise VerifiedManifestError(
            "trusted manifest verification failed"
        ) from None
