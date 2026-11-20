"""Test-only trusted manifest pipeline boundary regression."""

import base64
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from app.infrastructure.database.trust.manifest_loader import (
    load_manifest_file,
)
from app.infrastructure.database.trust.manifest_signature import (
    ManifestSignatureEnvelope,
    ManifestSignatureError,
    canonicalize_manifest_payload,
    verify_manifest_signature,
)
from app.infrastructure.database.trust.trusted_key_store import (
    TrustedKeyError,
    resolve_trusted_public_key,
)


_TEST_SEED = bytes(range(32))
_TEST_KEY_ID = "local-test-key-01"
_TEST_NOW = datetime(2026, 12, 1, tzinfo=timezone.utc)


class PipelineBoundaryError(ValueError):
    """Test harness security-boundary rejection."""


def _valid_payload():
    return {
        "schema_version": 1,
        "target": {
            "target_id": "smart-iot-integration",
            "environment": "testing",
            "manifest_version": 1,
        },
        "connection": {
            "database": "smart_iot_integration_test",
            "hostname": "127.0.0.1",
            "port": 5432,
            "tls_server_name": None,
        },
        "cluster": {
            "postgresql_major": 18,
            "system_identifier": "1234567890123456789",
            "data_directory": "/data/postgresql/18/main",
            "instance_identity": "local-main-18",
            "is_standby": False,
        },
        "authorization": {
            "login_role": "smart_iot_test_migrator",
            "effective_role": "smart_iot_test_owner",
            "allowed_operations": ["migration"],
        },
        "isolation": {
            "level": "database",
            "shared_cluster_with_production": True,
            "production_database": "smart_iot",
        },
        "validity": {
            "issued_at": "2026-11-18T00:00:00Z",
            "expires_at": "2027-11-18T00:00:00Z",
        },
    }


def _private_key():
    return Ed25519PrivateKey.from_private_bytes(_TEST_SEED)


def _public_key_bytes():
    return _private_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _registry(status="active"):
    return [{
        "key_id": _TEST_KEY_ID,
        "algorithm": "Ed25519",
        "status": status,
        "public_key": base64.b64encode(
            _public_key_bytes()
        ).decode("ascii"),
        "not_before": "2026-01-01T00:00:00Z",
        "not_after": "2027-12-31T23:59:59Z",
    }]


def _signed_envelope(payload, key_id=_TEST_KEY_ID):
    signature = _private_key().sign(
        canonicalize_manifest_payload(payload)
    )
    return {
        "key_id": key_id,
        "algorithm": "Ed25519",
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def _write_manifest(path, payload=None):
    data = _valid_payload() if payload is None else payload
    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )
    return path


def _run_test_pipeline(
    path,
    envelope,
    registry,
    *,
    selected_key_id,
    now=_TEST_NOW,
    resolver=resolve_trusted_public_key,
    verifier=verify_manifest_signature,
):
    """Test harness only; this is not a production orchestrator."""
    manifest = load_manifest_file(path, now=now)

    payload = manifest.model_dump(mode="json")
    parsed_envelope = ManifestSignatureEnvelope.model_validate(
        envelope
    )

    # Explicitly bind the caller-selected key to the signed envelope.
    if parsed_envelope.key_id != selected_key_id:
        raise PipelineBoundaryError(
            "signature key_id does not match selected key_id"
        )

    public_key = resolver(
        selected_key_id,
        registry,
        now=now,
    )

    verifier(
        payload,
        parsed_envelope,
        public_key,
    )

    return manifest


def test_pipeline_accepts_valid_manifest_and_signature(tmp_path):
    payload = _valid_payload()
    path = _write_manifest(tmp_path / "manifest.json", payload)
    envelope = _signed_envelope(payload)

    result = _run_test_pipeline(
        path,
        envelope,
        _registry(),
        selected_key_id=_TEST_KEY_ID,
    )

    assert result.target.environment == "testing"


def test_invalid_schema_stops_before_key_resolution(tmp_path):
    payload = _valid_payload()
    payload["unexpected"] = True
    path = _write_manifest(tmp_path / "manifest.json", payload)

    resolver = Mock(side_effect=resolve_trusted_public_key)

    with pytest.raises(ValueError):
        _run_test_pipeline(
            path,
            _signed_envelope(payload),
            _registry(),
            selected_key_id=_TEST_KEY_ID,
            resolver=resolver,
        )

    resolver.assert_not_called()


def test_revoked_key_stops_before_signature_verification(tmp_path):
    payload = _valid_payload()
    path = _write_manifest(tmp_path / "manifest.json", payload)

    verifier = Mock(side_effect=verify_manifest_signature)

    with pytest.raises(TrustedKeyError, match="revoked"):
        _run_test_pipeline(
            path,
            _signed_envelope(payload),
            _registry(status="revoked"),
            selected_key_id=_TEST_KEY_ID,
            verifier=verifier,
        )

    verifier.assert_not_called()


def test_key_id_mismatch_stops_before_resolution_and_verification(
    tmp_path,
):
    payload = _valid_payload()
    path = _write_manifest(tmp_path / "manifest.json", payload)

    resolver = Mock(side_effect=resolve_trusted_public_key)
    verifier = Mock(side_effect=verify_manifest_signature)

    with pytest.raises(PipelineBoundaryError, match="key_id"):
        _run_test_pipeline(
            path,
            _signed_envelope(payload, key_id="different-test-key"),
            _registry(),
            selected_key_id=_TEST_KEY_ID,
            resolver=resolver,
            verifier=verifier,
        )

    resolver.assert_not_called()
    verifier.assert_not_called()


def test_invalid_signature_is_rejected_after_key_resolution(tmp_path):
    payload = _valid_payload()
    path = _write_manifest(tmp_path / "manifest.json", payload)

    envelope = _signed_envelope(payload)
    envelope["signature"] = base64.b64encode(
        bytes(64)
    ).decode("ascii")

    resolver = Mock(side_effect=resolve_trusted_public_key)
    verifier = Mock(side_effect=verify_manifest_signature)

    with pytest.raises(ManifestSignatureError):
        _run_test_pipeline(
            path,
            envelope,
            _registry(),
            selected_key_id=_TEST_KEY_ID,
            resolver=resolver,
            verifier=verifier,
        )

    resolver.assert_called_once()
    verifier.assert_called_once()


def test_expired_key_stops_before_signature_verification(tmp_path):
    payload = _valid_payload()
    path = _write_manifest(tmp_path / "manifest.json", payload)

    verifier = Mock(side_effect=verify_manifest_signature)

    expired_registry = [{
        **_registry()[0],
        "not_after": "2026-12-01T00:00:00Z",
    }]

    with pytest.raises(TrustedKeyError, match="expired"):
        _run_test_pipeline(
            path,
            _signed_envelope(payload),
            expired_registry,
            selected_key_id=_TEST_KEY_ID,
            verifier=verifier,
        )

    verifier.assert_not_called()
