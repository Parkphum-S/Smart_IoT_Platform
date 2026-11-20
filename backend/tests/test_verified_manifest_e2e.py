"""End-to-end tests for the public trusted manifest API."""

import base64
import hashlib
import json

import pytest

from test_manifest_bundle import _setup, _json_bytes
from test_verified_manifest import (
    _TEST_NOW,
    _valid_payload,
    _signature_envelope,
    _registry_record,
)

from app.infrastructure.database.trust import (
    VerifiedManifest,
    VerifiedManifestError,
    load_verified_manifest,
)


def _prepare_real_bundle(tmp_path, *, corrupt_signature=False):
    config, _, signature_path, registry_path = _setup(tmp_path)

    payload = _valid_payload()
    signature = _signature_envelope(payload).model_dump(mode="json")
    registry = [_registry_record().model_dump(mode="json")]

    if corrupt_signature:
        raw_signature = bytearray(
            base64.b64decode(signature["signature"])
        )
        raw_signature[0] ^= 1
        signature["signature"] = base64.b64encode(
            bytes(raw_signature)
        ).decode("ascii")

    signature_bytes = _json_bytes(signature)
    registry_bytes = _json_bytes(registry)

    generation_dir = signature_path.parent
    descriptor_path = generation_dir / "descriptor.json"

    generation_dir.chmod(0o700)

    signature_path.chmod(0o600)
    signature_path.write_bytes(signature_bytes)

    registry_path.chmod(0o600)
    registry_path.write_bytes(registry_bytes)

    descriptor = json.loads(
        descriptor_path.read_text(encoding="utf-8")
    )
    descriptor["signature_sha256"] = hashlib.sha256(
        signature_bytes
    ).hexdigest()
    descriptor["registry_sha256"] = hashlib.sha256(
        registry_bytes
    ).hexdigest()

    descriptor_path.chmod(0o600)
    descriptor_path.write_bytes(_json_bytes(descriptor))

    signature_path.chmod(0o400)
    registry_path.chmod(0o400)
    descriptor_path.chmod(0o400)
    generation_dir.chmod(0o500)

    return config


def test_public_api_loads_and_verifies_real_local_bundle(tmp_path):
    config = _prepare_real_bundle(tmp_path)

    result = load_verified_manifest(config, now=_TEST_NOW)

    assert isinstance(result, VerifiedManifest)
    assert result.manifest.target.environment == "testing"
    assert result.key_id == "local-test-key-01"
    assert result.algorithm == "Ed25519"
    assert result.verified_at == _TEST_NOW
    assert len(result.manifest_digest) == 64


def test_public_api_rejects_invalid_ed25519_signature(tmp_path):
    config = _prepare_real_bundle(
        tmp_path,
        corrupt_signature=True,
    )

    with pytest.raises(VerifiedManifestError):
        load_verified_manifest(config, now=_TEST_NOW)
