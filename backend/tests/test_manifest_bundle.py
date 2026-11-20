"""Tests for secure trusted manifest bundle loading."""

import base64
import hashlib
import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

import app.infrastructure.database.trust.manifest_bundle as bundle_module

from app.infrastructure.database.trust.manifest_bundle import (
    ManifestBundleError,
    TrustedManifestBundle,
    load_trusted_manifest_bundle,
)
from app.infrastructure.database.trust.trusted_config import (
    TrustedOrchestratorConfig,
)


NOW = datetime(2026, 11, 18, tzinfo=timezone.utc)


def _payload():
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


def _signature(key_id="local-test-key-01"):
    return {
        "key_id": key_id,
        "algorithm": "Ed25519",
        "signature": base64.b64encode(bytes(64)).decode("ascii"),
    }


def _record(key_id="local-test-key-01"):
    return {
        "key_id": key_id,
        "algorithm": "Ed25519",
        "status": "active",
        "public_key": base64.b64encode(bytes(range(32))).decode("ascii"),
        "not_before": "2026-01-01T00:00:00Z",
        "not_after": "2027-12-31T23:59:59Z",
    }


def _json_bytes(data):
    return json.dumps(data, separators=(",", ":")).encode("utf-8")


def _write_json(path, data):
    path.write_bytes(_json_bytes(data))
    path.chmod(0o400)
    return path


def _setup(tmp_path, *, signature=None, registry=None):
    bundle_root = tmp_path / "trusted-bundle"
    generations_dir = bundle_root / "generations"
    generation_dir = generations_dir / "generation-001"

    bundle_root.mkdir(mode=0o700)
    generations_dir.mkdir(mode=0o700)
    generation_dir.mkdir(mode=0o700)

    bundle_root.chmod(0o700)
    generations_dir.chmod(0o700)

    manifest_path = _write_json(
        generation_dir / "manifest.json",
        _payload(),
    )
    signature_path = _write_json(
        generation_dir / "signature.json",
        _signature() if signature is None else signature,
    )
    registry_path = _write_json(
        generation_dir / "registry.json",
        [_record()] if registry is None else registry,
    )

    descriptor = {
        "schema_version": 1,
        "generation_id": "generation-001",
        "manifest_sha256": hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest(),
        "signature_sha256": hashlib.sha256(
            signature_path.read_bytes()
        ).hexdigest(),
        "registry_sha256": hashlib.sha256(
            registry_path.read_bytes()
        ).hexdigest(),
        "selected_key_id": "local-test-key-01",
        "created_at": "2026-11-18T00:00:00Z",
    }

    _write_json(generation_dir / "descriptor.json", descriptor)
    generation_dir.chmod(0o500)

    current_path = bundle_root / "CURRENT"
    current_path.write_bytes(b"generation-001\n")
    current_path.chmod(0o600)

    config = TrustedOrchestratorConfig(
        bundle_root=str(bundle_root),
        selected_key_id="local-test-key-01",
        expected_environment="testing",
    )

    return config, manifest_path, signature_path, registry_path


def _replace_generation_file(path, raw_data):
    generation_dir = path.parent
    descriptor_path = generation_dir / "descriptor.json"

    path.chmod(0o600)
    path.write_bytes(raw_data)
    path.chmod(0o400)

    descriptor = json.loads(
        descriptor_path.read_text(encoding="utf-8")
    )

    digest_field = {
        "manifest.json": "manifest_sha256",
        "signature.json": "signature_sha256",
        "registry.json": "registry_sha256",
    }[path.name]

    descriptor[digest_field] = hashlib.sha256(raw_data).hexdigest()

    descriptor_path.chmod(0o600)
    descriptor_path.write_bytes(_json_bytes(descriptor))
    descriptor_path.chmod(0o400)


def _set_generation_directory_writable(path, writable):
    path.chmod(0o700 if writable else 0o500)

def test_loads_valid_bundle(tmp_path):
    config, *_ = _setup(tmp_path)

    result = load_trusted_manifest_bundle(config)

    assert isinstance(result, TrustedManifestBundle)
    assert result.manifest.target.environment == "testing"
    assert result.signature.key_id == "local-test-key-01"
    assert len(result.key_registry) == 1
    assert result.selected_key_id == "local-test-key-01"


def test_registry_snapshot_is_tuple_and_frozen(tmp_path):
    config, *_ = _setup(tmp_path)

    result = load_trusted_manifest_bundle(config)

    assert isinstance(result.key_registry, tuple)

    with pytest.raises(ValidationError):
        result.selected_key_id = "changed"

    with pytest.raises(ValidationError):
        result.manifest.target.target_id = "changed"


def test_rejects_non_configuration_input():
    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(object())


def test_rejects_signature_key_id_mismatch(tmp_path):
    config, *_ = _setup(
        tmp_path,
        signature=_signature("different-key"),
    )

    with pytest.raises(ManifestBundleError, match="key_id"):
        load_trusted_manifest_bundle(config)


def test_rejects_selected_key_absent_from_registry(tmp_path):
    config, *_ = _setup(
        tmp_path,
        registry=[_record("another-key")],
    )

    with pytest.raises(ManifestBundleError, match="absent"):
        load_trusted_manifest_bundle(config)


def test_rejects_duplicate_registry_key_ids(tmp_path):
    config, *_ = _setup(
        tmp_path,
        registry=[_record(), _record()],
    )

    with pytest.raises(ManifestBundleError, match="duplicate"):
        load_trusted_manifest_bundle(config)


def test_rejects_empty_registry(tmp_path):
    config, *_ = _setup(tmp_path, registry=[])

    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(config)


def test_rejects_registry_with_unknown_fields(tmp_path):
    record = _record()
    record["unexpected"] = True
    config, *_ = _setup(tmp_path, registry=[record])

    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(config)


def test_rejects_duplicate_json_keys_in_signature(tmp_path):
    config, _, signature_path, _ = _setup(tmp_path)

    raw_data = (
        '{"key_id":"local-test-key-01","key_id":"other",'
        '"algorithm":"Ed25519","signature":"'
        + base64.b64encode(bytes(64)).decode("ascii")
        + '"}'
    ).encode("utf-8")

    _replace_generation_file(signature_path, raw_data)

    with pytest.raises(ManifestBundleError, match="duplicate"):
        load_trusted_manifest_bundle(config)

def test_rejects_utf8_bom_in_registry(tmp_path):
    config, _, _, registry_path = _setup(tmp_path)

    _replace_generation_file(
        registry_path,
        bytes.fromhex("efbbbf") + _json_bytes([_record()]),
    )

    with pytest.raises(ManifestBundleError, match="BOM"):
        load_trusted_manifest_bundle(config)

def test_rejects_registry_size_limit(tmp_path):
    config, *_ = _setup(tmp_path)
    config = config.model_copy(update={"max_registry_bytes": 16})

    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(config)

def test_rejects_signature_symlink(tmp_path):
    config, _, signature_path, _ = _setup(tmp_path)

    real_path = tmp_path / "real-signature.json"
    real_path.write_bytes(signature_path.read_bytes())
    real_path.chmod(0o400)

    _set_generation_directory_writable(signature_path.parent, True)
    signature_path.unlink()
    signature_path.symlink_to(real_path)
    _set_generation_directory_writable(signature_path.parent, False)

    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(config)

def test_rejects_directory_as_registry(tmp_path):
    config, _, _, registry_path = _setup(tmp_path)

    _set_generation_directory_writable(registry_path.parent, True)
    registry_path.unlink()
    registry_path.mkdir(mode=0o500)
    _set_generation_directory_writable(registry_path.parent, False)

    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(config)

def test_rejects_invalid_signature_schema(tmp_path):
    config, _, signature_path, _ = _setup(tmp_path)

    _replace_generation_file(
        signature_path,
        b'{"key_id":"bad"}',
    )

    with pytest.raises(ManifestBundleError):
        load_trusted_manifest_bundle(config)

def test_snapshot_rejects_list_for_registry(tmp_path):
    config, *_ = _setup(tmp_path)
    bundle = load_trusted_manifest_bundle(config)

    with pytest.raises(ValidationError):
        TrustedManifestBundle.model_validate({
            "manifest": bundle.manifest,
            "signature": bundle.signature,
            "key_registry": list(bundle.key_registry),
            "selected_key_id": bundle.selected_key_id,
        })


def test_snapshot_rejects_extra_fields(tmp_path):
    config, *_ = _setup(tmp_path)
    bundle = load_trusted_manifest_bundle(config)

    with pytest.raises(ValidationError):
        TrustedManifestBundle.model_validate({
            "manifest": bundle.manifest,
            "signature": bundle.signature,
            "key_registry": bundle.key_registry,
            "selected_key_id": bundle.selected_key_id,
            "unexpected": True,
        })


def test_injected_now_is_forwarded_to_manifest_loader(
    tmp_path,
    monkeypatch,
):
    config, *_ = _setup(tmp_path)
    injected_now = NOW
    original_loader = bundle_module.load_manifest_bytes
    observed = {}

    def capture_loader(raw_data, *, max_bytes, now=None):
        observed["now"] = now
        return original_loader(
            raw_data,
            max_bytes=max_bytes,
            now=now,
        )

    monkeypatch.setattr(
        bundle_module,
        "load_manifest_bytes",
        capture_loader,
    )

    load_trusted_manifest_bundle(config, now=injected_now)

    assert observed["now"] is injected_now
