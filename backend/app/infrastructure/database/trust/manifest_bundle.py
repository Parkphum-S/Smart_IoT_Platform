"""Secure loading and immutable snapshot of a trusted manifest bundle."""

from __future__ import annotations

import json
from datetime import datetime
from typing import NoReturn

from pydantic import StrictStr, ValidationError

from .bundle_snapshot import (
    TrustedBundleSnapshotError,
    load_trusted_bundle_snapshot,
)
from .manifest_loader import ManifestLoadError, load_manifest_bytes
from .manifest_signature import ManifestSignatureEnvelope
from .trusted_config import (
    TrustedConfigurationError,
    TrustedOrchestratorConfig,
)
from .trusted_key_store import (
    TrustedKeyError,
    TrustedPublicKeyRecord,
)
from .trusted_manifest import StrictManifestModel, TrustedManifestPayload


class ManifestBundleError(ValueError):
    """Raised when a trusted manifest bundle cannot be loaded safely."""


class TrustedManifestBundle(StrictManifestModel):
    """Strict, frozen snapshot of the independently loaded trust files."""

    manifest: TrustedManifestPayload
    signature: ManifestSignatureEnvelope
    key_registry: tuple[TrustedPublicKeyRecord, ...]
    selected_key_id: StrictStr


def _reject_constant(value: str) -> NoReturn:
    raise ManifestBundleError("non-standard JSON numeric constant rejected")


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in pairs:
        if key in result:
            raise ManifestBundleError("duplicate JSON object key rejected")
        result[key] = value

    return result


def _load_json_bytes(raw_data: bytes, max_bytes: int) -> object:
    if type(raw_data) is not bytes:
        raise ManifestBundleError("trusted file data must be bytes")

    if type(max_bytes) is not int or max_bytes < 1:
        raise ManifestBundleError("invalid trusted file size limit")

    if len(raw_data) > max_bytes:
        raise ManifestBundleError("trusted file exceeds size limit")

    if raw_data.startswith(bytes.fromhex("efbbbf")):
        raise ManifestBundleError("UTF-8 BOM is not accepted")

    try:
        decoded = raw_data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ManifestBundleError("trusted file must be valid UTF-8") from exc

    try:
        return json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except ManifestBundleError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ManifestBundleError("trusted file JSON is invalid") from exc


def load_trusted_manifest_bundle(
    config: TrustedOrchestratorConfig,
    *,
    now: datetime | None = None,
) -> TrustedManifestBundle:
    """Load and structurally validate one generation-consistent bundle.

    Signature verification and public-key resolution are deliberately
    delegated to the later trusted orchestrator.
    """
    if not isinstance(config, TrustedOrchestratorConfig):
        raise ManifestBundleError("trusted configuration is required")

    if config.expected_environment != "testing":
        raise ManifestBundleError("unsupported trusted environment")

    try:
        snapshot = load_trusted_bundle_snapshot(
            config.bundle_root,
            max_manifest_bytes=config.max_manifest_bytes,
            max_signature_bytes=config.max_signature_bytes,
            max_registry_bytes=config.max_registry_bytes,
        )

        if snapshot.descriptor.generation_id != snapshot.generation_id:
            raise ManifestBundleError(
                "bundle descriptor generation mismatch"
            )

        if snapshot.descriptor.selected_key_id != config.selected_key_id:
            raise ManifestBundleError(
                "bundle descriptor key_id does not match configured key_id"
            )

        manifest = load_manifest_bytes(
            snapshot.manifest_bytes,
            max_bytes=config.max_manifest_bytes,
            now=now,
        )

        signature_data = _load_json_bytes(
            snapshot.signature_bytes,
            config.max_signature_bytes,
        )
        signature = ManifestSignatureEnvelope.model_validate(
            signature_data
        )

        registry_data = _load_json_bytes(
            snapshot.registry_bytes,
            config.max_registry_bytes,
        )

        if type(registry_data) is not list or not registry_data:
            raise ManifestBundleError(
                "trusted key registry must be a nonempty JSON array"
            )

        records: list[TrustedPublicKeyRecord] = []
        seen: set[str] = set()

        for item in registry_data:
            record = TrustedPublicKeyRecord.model_validate(item)

            if record.key_id in seen:
                raise ManifestBundleError(
                    "duplicate key_id in trusted registry"
                )

            seen.add(record.key_id)
            records.append(record)

        if signature.key_id != config.selected_key_id:
            raise ManifestBundleError(
                "signature key_id does not match selected key_id"
            )

        if config.selected_key_id not in seen:
            raise ManifestBundleError(
                "selected key_id is absent from trusted registry"
            )

        return TrustedManifestBundle(
            manifest=manifest,
            signature=signature,
            key_registry=tuple(records),
            selected_key_id=config.selected_key_id,
        )

    except ManifestBundleError:
        raise
    except (
        ManifestLoadError,
        TrustedBundleSnapshotError,
        TrustedConfigurationError,
        TrustedKeyError,
        ValidationError,
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        raise ManifestBundleError(
            "trusted manifest bundle validation failed"
        ) from exc
