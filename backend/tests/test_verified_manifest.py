"""Tests for the verified trusted manifest provider."""

import base64
import hashlib

import pytest
from unittest.mock import Mock

from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from pydantic import ValidationError

from app.infrastructure.database.trust.manifest_bundle import (
    TrustedManifestBundle,
)
from app.infrastructure.database.trust.manifest_signature import (
    ManifestSignatureEnvelope,
    canonicalize_manifest_payload,
)
from app.infrastructure.database.trust.trusted_key_store import (
    TrustedPublicKeyRecord,
)
from app.infrastructure.database.trust.trusted_manifest import (
    TrustedManifestPayload,
)
from app.infrastructure.database.trust import (
    verified_manifest as verified_module,
)
from app.infrastructure.database.trust.verified_manifest import (
    VerifiedManifest,
    VerifiedManifestError,
    verify_trusted_manifest_bundle,
)


_TEST_SEED = bytes(range(32))
_TEST_KEY_ID = "local-test-key-01"
_TEST_NOW = datetime(2026, 12, 1, tzinfo=timezone.utc)


def _private_key():
    return Ed25519PrivateKey.from_private_bytes(_TEST_SEED)


def _public_key_bytes():
    return _private_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


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


def _signature_envelope(payload):
    signature = _private_key().sign(
        canonicalize_manifest_payload(payload)
    )

    return ManifestSignatureEnvelope.model_validate({
        "key_id": _TEST_KEY_ID,
        "algorithm": "Ed25519",
        "signature": base64.b64encode(
            signature
        ).decode("ascii"),
    })


def _registry_record(
    *,
    status="active",
    not_before="2026-01-01T00:00:00Z",
    not_after="2027-12-31T23:59:59Z",
):
    return TrustedPublicKeyRecord.model_validate({
        "key_id": _TEST_KEY_ID,
        "algorithm": "Ed25519",
        "status": status,
        "public_key": base64.b64encode(
            _public_key_bytes()
        ).decode("ascii"),
        "not_before": not_before,
        "not_after": not_after,
    })


def _bundle(
    *,
    payload=None,
    status="active",
    not_before="2026-01-01T00:00:00Z",
    not_after="2027-12-31T23:59:59Z",
    envelope=None,
):
    data = _valid_payload() if payload is None else payload

    manifest = TrustedManifestPayload.model_validate(data)

    signature = (
        _signature_envelope(data)
        if envelope is None
        else envelope
    )

    return TrustedManifestBundle(
        manifest=manifest,
        signature=signature,
        key_registry=(
            _registry_record(
                status=status,
                not_before=not_before,
                not_after=not_after,
            ),
        ),
        selected_key_id=_TEST_KEY_ID,
    )


def test_valid_bundle_returns_verified_manifest():
    bundle = _bundle()

    result = verify_trusted_manifest_bundle(
        bundle,
        now=_TEST_NOW,
    )

    assert isinstance(result, VerifiedManifest)
    assert result.manifest.target.environment == "testing"
    assert result.key_id == _TEST_KEY_ID
    assert result.algorithm == "Ed25519"
    assert result.verified_at == _TEST_NOW


def test_digest_matches_rfc8785_canonical_payload():
    bundle = _bundle()

    result = verify_trusted_manifest_bundle(
        bundle,
        now=_TEST_NOW,
    )

    payload = bundle.manifest.model_dump(mode="json")
    canonical = canonicalize_manifest_payload(payload)

    expected = hashlib.sha256(canonical).hexdigest()

    assert result.manifest_digest == expected
    assert len(result.manifest_digest) == 64


def test_modified_manifest_is_rejected():
    original_payload = _valid_payload()
    envelope = _signature_envelope(original_payload)

    modified_payload = _valid_payload()
    modified_payload["target"]["manifest_version"] = 2

    bundle = _bundle(
        payload=modified_payload,
        envelope=envelope,
    )

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_invalid_signature_is_rejected():
    payload = _valid_payload()

    invalid_envelope = ManifestSignatureEnvelope.model_validate({
        "key_id": _TEST_KEY_ID,
        "algorithm": "Ed25519",
        "signature": base64.b64encode(
            bytes(64)
        ).decode("ascii"),
    })

    bundle = _bundle(
        payload=payload,
        envelope=invalid_envelope,
    )

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_revoked_key_is_rejected():
    bundle = _bundle(status="revoked")

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_expired_key_is_rejected():
    bundle = _bundle(
        not_after="2026-11-30T00:00:00Z",
    )

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_not_yet_valid_key_is_rejected():
    bundle = _bundle(
        not_before="2027-01-01T00:00:00Z",
    )

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_expired_manifest_is_rejected():
    payload = _valid_payload()
    payload["validity"]["expires_at"] = "2026-11-30T00:00:00Z"

    bundle = _bundle(payload=payload)

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_future_manifest_is_rejected():
    payload = _valid_payload()
    payload["validity"]["issued_at"] = "2027-01-01T00:00:00Z"
    payload["validity"]["expires_at"] = "2027-12-01T00:00:00Z"

    bundle = _bundle(payload=payload)

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )


def test_naive_verification_time_is_rejected():
    bundle = _bundle()

    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            bundle,
            now=datetime(2026, 12, 1),
        )


def test_wrong_bundle_type_is_rejected():
    with pytest.raises(VerifiedManifestError):
        verify_trusted_manifest_bundle(
            object(),
            now=_TEST_NOW,
        )


def test_verified_manifest_rejects_invalid_digest():
    with pytest.raises(ValidationError):
        VerifiedManifest(
            manifest=TrustedManifestPayload.model_validate(
                _valid_payload()
            ),
            key_id=_TEST_KEY_ID,
            algorithm="Ed25519",
            manifest_digest="invalid",
            verified_at=_TEST_NOW,
        )


def test_verified_manifest_rejects_naive_verified_at():
    with pytest.raises(ValidationError):
        VerifiedManifest(
            manifest=TrustedManifestPayload.model_validate(
                _valid_payload()
            ),
            key_id=_TEST_KEY_ID,
            algorithm="Ed25519",
            manifest_digest="a" * 64,
            verified_at=datetime(2026, 12, 1),
        )


def test_verified_manifest_is_frozen():
    result = verify_trusted_manifest_bundle(
        _bundle(),
        now=_TEST_NOW,
    )

    with pytest.raises(ValidationError):
        result.key_id = "changed"

    with pytest.raises(ValidationError):
        result.manifest.target.manifest_version = 99


def test_verified_at_is_normalized_to_utc():
    from datetime import timedelta

    offset_time = datetime(
        2026, 12, 1, 19, 0,
        tzinfo=timezone(timedelta(hours=7)),
    )

    result = verify_trusted_manifest_bundle(
        _bundle(),
        now=offset_time,
    )

    expected_utc = offset_time.astimezone(timezone.utc)
    assert result.verified_at == expected_utc
    assert result.verified_at.utcoffset().total_seconds() == 0

def test_key_id_mismatch_stops_before_resolution_and_verification(
    monkeypatch,
):
    bundle = _bundle()

    mismatched_signature = bundle.signature.model_copy(
        update={"key_id": "different-test-key"}
    )
    bundle = bundle.model_copy(
        update={"signature": mismatched_signature}
    )

    resolver = Mock()
    verifier = Mock()

    monkeypatch.setattr(
        verified_module,
        "resolve_trusted_public_key",
        resolver,
    )
    monkeypatch.setattr(
        verified_module,
        "verify_manifest_signature",
        verifier,
    )

    with pytest.raises(VerifiedManifestError, match="key_id"):
        verify_trusted_manifest_bundle(
            bundle,
            now=_TEST_NOW,
        )

    resolver.assert_not_called()
    verifier.assert_not_called()


def test_manifest_validator_and_key_resolver_receive_same_time(
    monkeypatch,
):
    observed = {}

    original_validator = verified_module.validate_manifest_payload
    original_resolver = verified_module.resolve_trusted_public_key

    def capture_validator(payload, *, now=None):
        observed["validator_now"] = now
        return original_validator(payload, now=now)

    def capture_resolver(key_id, registry, *, now=None):
        observed["resolver_now"] = now
        return original_resolver(
            key_id,
            registry,
            now=now,
        )

    monkeypatch.setattr(
        verified_module,
        "validate_manifest_payload",
        capture_validator,
    )
    monkeypatch.setattr(
        verified_module,
        "resolve_trusted_public_key",
        capture_resolver,
    )

    result = verify_trusted_manifest_bundle(
        _bundle(),
        now=_TEST_NOW,
    )

    assert isinstance(result, VerifiedManifest)
    assert observed["validator_now"] == _TEST_NOW
    assert observed["resolver_now"] == _TEST_NOW
    assert observed["validator_now"] == observed["resolver_now"]
