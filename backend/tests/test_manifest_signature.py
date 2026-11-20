"""Deterministic test-key coverage for Ed25519 verification."""

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from pydantic import ValidationError

from app.infrastructure.database.trust.manifest_signature import (
    ManifestSignatureError,
    ManifestSignatureEnvelope,
    canonicalize_manifest_payload,
    verify_manifest_signature,
)


# Fixed test-only seed. Never use this key outside unit tests.
_TEST_PRIVATE_SEED = bytes(range(32))


def _test_private_key():
    return Ed25519PrivateKey.from_private_bytes(_TEST_PRIVATE_SEED)


def _test_public_key_bytes():
    return _test_private_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _signed_envelope(payload):
    signature = _test_private_key().sign(
        canonicalize_manifest_payload(payload)
    )
    return {
        "key_id": "unit-test-ed25519",
        "algorithm": "Ed25519",
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def test_rfc8785_canonicalization():
    result = canonicalize_manifest_payload({"b": 2, "a": 1})
    assert result == b'{"a":1,"b":2}'


def test_valid_signature_is_accepted():
    payload = {"schema_version": 1, "target": {"environment": "testing"}}

    assert verify_manifest_signature(
        payload,
        _signed_envelope(payload),
        _test_public_key_bytes(),
    ) is True


def test_modified_payload_is_rejected():
    payload = {"schema_version": 1, "target": {"environment": "testing"}}
    envelope = _signed_envelope(payload)
    payload["target"]["environment"] = "production"

    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature(
            payload, envelope, _test_public_key_bytes()
        )


def test_wrong_public_key_is_rejected():
    payload = {"schema_version": 1}
    wrong_key = Ed25519PrivateKey.from_private_bytes(
        bytes(reversed(range(32)))
    ).public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature(
            payload, _signed_envelope(payload), wrong_key
        )


def test_invalid_public_key_length_is_rejected():
    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature({}, {}, b"short")


def test_non_bytes_public_key_is_rejected():
    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature({}, {}, "not-a-key")


def test_non_object_payload_is_rejected():
    with pytest.raises(ManifestSignatureError):
        canonicalize_manifest_payload([])


@pytest.mark.parametrize(
    "algorithm",
    ["RSA", "Ed25519ph", "ed25519", ""],
)
def test_unsupported_algorithm_is_rejected(algorithm):
    envelope = _signed_envelope({})
    envelope["algorithm"] = algorithm

    with pytest.raises(ValidationError):
        ManifestSignatureEnvelope.model_validate(envelope)


@pytest.mark.parametrize(
    "key_id",
    ["", "../key", "key with spaces", "/etc/passwd"],
)
def test_invalid_key_id_is_rejected(key_id):
    envelope = _signed_envelope({})
    envelope["key_id"] = key_id

    with pytest.raises(ValidationError):
        ManifestSignatureEnvelope.model_validate(envelope)


@pytest.mark.parametrize(
    "signature",
    ["", "not-base64!", "AAAA"],
)
def test_invalid_signature_encoding_is_rejected(signature):
    envelope = _signed_envelope({})
    envelope["signature"] = signature

    with pytest.raises(ValidationError):
        ManifestSignatureEnvelope.model_validate(envelope)


def test_unknown_envelope_field_is_rejected():
    envelope = _signed_envelope({})
    envelope["unexpected"] = True

    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature(
            {}, envelope, _test_public_key_bytes()
        )


def test_signature_is_bound_to_canonical_payload():
    first = {"b": 2, "a": 1}
    second = {"a": 1, "b": 2}

    assert canonicalize_manifest_payload(first) == (
        canonicalize_manifest_payload(second)
    )

    envelope = _signed_envelope(first)

    assert verify_manifest_signature(
        second, envelope, _test_public_key_bytes()
    ) is True
