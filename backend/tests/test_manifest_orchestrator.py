"""Tests for trusted manifest orchestration."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.infrastructure.database.trust import manifest_orchestrator as orchestrator


def test_load_verified_manifest_calls_loader_then_verifier(monkeypatch):
    config = Mock()
    bundle = object()
    verified = object()
    now = datetime(2026, 12, 1, tzinfo=timezone.utc)

    loader = Mock(return_value=bundle)
    verifier = Mock(return_value=verified)

    monkeypatch.setattr(
        orchestrator,
        "load_trusted_manifest_bundle",
        loader,
    )
    monkeypatch.setattr(
        orchestrator,
        "verify_trusted_manifest_bundle",
        verifier,
    )

    result = orchestrator.load_verified_manifest(config, now=now)

    assert result is verified
    loader.assert_called_once_with(config, now=now)
    verifier.assert_called_once_with(bundle, now=now)


def test_verification_is_not_called_when_loading_fails(monkeypatch):
    config = Mock()
    error = ValueError("bundle loading failed")

    loader = Mock(side_effect=error)
    verifier = Mock()

    monkeypatch.setattr(
        orchestrator,
        "load_trusted_manifest_bundle",
        loader,
    )
    monkeypatch.setattr(
        orchestrator,
        "verify_trusted_manifest_bundle",
        verifier,
    )

    with pytest.raises(ValueError, match="bundle loading failed"):
        orchestrator.load_verified_manifest(config)

    verifier.assert_not_called()


def test_verification_error_is_propagated(monkeypatch):
    config = Mock()
    bundle = object()
    error = ValueError("verification failed")

    monkeypatch.setattr(
        orchestrator,
        "load_trusted_manifest_bundle",
        Mock(return_value=bundle),
    )
    monkeypatch.setattr(
        orchestrator,
        "verify_trusted_manifest_bundle",
        Mock(side_effect=error),
    )

    with pytest.raises(ValueError, match="verification failed"):
        orchestrator.load_verified_manifest(config)
