"""Orchestrate trusted manifest loading and verification."""

from __future__ import annotations

from datetime import datetime

from .manifest_bundle import load_trusted_manifest_bundle
from .trusted_config import TrustedOrchestratorConfig
from .verified_manifest import (
    VerifiedManifest,
    verify_trusted_manifest_bundle,
)


def load_verified_manifest(
    config: TrustedOrchestratorConfig,
    *,
    now: datetime | None = None,
) -> VerifiedManifest:
    """Load a trusted bundle and return it only after verification."""

    bundle = load_trusted_manifest_bundle(config, now=now)

    return verify_trusted_manifest_bundle(
        bundle,
        now=now,
    )
