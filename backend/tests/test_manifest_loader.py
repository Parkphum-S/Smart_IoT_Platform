"""Mock regression tests for secure manifest file loading."""

import json
import os
from datetime import datetime, timezone

import pytest

from app.infrastructure.database.trust.manifest_loader import (
    DEFAULT_MAX_MANIFEST_BYTES,
    ManifestLoadError,
    load_manifest_bytes,
    load_manifest_file,
)


def valid_payload():
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



TEST_NOW = datetime(
    2026, 11, 18, 12, 0, tzinfo=timezone.utc
)


def _write_payload(path, payload=None):
    data = valid_payload() if payload is None else payload
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_valid_manifest(tmp_path):
    path = _write_payload(tmp_path / "manifest.json")

    result = load_manifest_file(path, now=TEST_NOW)

    assert result.schema_version == 1
    assert result.target.environment == "testing"


def test_accepts_pathlike_input(tmp_path):
    path = _write_payload(tmp_path / "manifest.json")

    result = load_manifest_file(path, now=TEST_NOW)

    assert result.schema_version == 1


def test_loader_rejects_manifest_before_issued_at(tmp_path):
    payload = valid_payload()
    payload["validity"]["issued_at"] = "2026-11-18T12:00:01Z"
    path = _write_payload(tmp_path / "manifest.json", payload)
    with pytest.raises(ManifestLoadError, match="schema validation"):
        load_manifest_file(path, now=TEST_NOW)


def test_loader_rejects_manifest_at_expiry(tmp_path):
    payload = valid_payload()
    payload["validity"]["expires_at"] = "2026-11-18T12:00:00Z"
    path = _write_payload(tmp_path / "manifest.json", payload)
    with pytest.raises(ManifestLoadError, match="schema validation"):
        load_manifest_file(path, now=TEST_NOW)


def test_rejects_relative_path(tmp_path, monkeypatch):
    path = _write_payload(tmp_path / "manifest.json")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ManifestLoadError, match="absolute"):
        load_manifest_file("manifest.json")


def test_rejects_parent_traversal(tmp_path):
    path = _write_payload(tmp_path / "manifest.json")
    traversal = str(tmp_path / ".." / path.name)

    with pytest.raises(ManifestLoadError, match="components"):
        load_manifest_file(traversal)


def test_rejects_final_symlink(tmp_path):
    target = _write_payload(tmp_path / "target.json")
    link = tmp_path / "manifest.json"
    link.symlink_to(target)

    with pytest.raises(ManifestLoadError, match="securely"):
        load_manifest_file(link)


def test_rejects_intermediate_symlink(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    target = _write_payload(real_dir / "manifest.json")

    link_dir = tmp_path / "linked"
    link_dir.symlink_to(real_dir, target_is_directory=True)

    with pytest.raises(ManifestLoadError, match="securely"):
        load_manifest_file(link_dir / target.name)


def test_rejects_directory_as_manifest(tmp_path):
    directory = tmp_path / "manifest"
    directory.mkdir()

    with pytest.raises(ManifestLoadError, match="regular file"):
        load_manifest_file(directory)


def test_rejects_oversized_file(tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 128)

    with pytest.raises(ManifestLoadError, match="size limit"):
        load_manifest_file(path, max_bytes=64)


def test_rejects_invalid_max_bytes(tmp_path):
    path = _write_payload(tmp_path / "manifest.json")

    for value in (0, -1, True, 1.5):
        with pytest.raises(ManifestLoadError, match="max_bytes"):
            load_manifest_file(path, max_bytes=value)


def test_rejects_malformed_json(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"broken":', encoding="utf-8")

    with pytest.raises(ManifestLoadError, match="JSON is invalid"):
        load_manifest_file(path)


def test_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")

    with pytest.raises(ManifestLoadError, match="duplicate"):
        load_manifest_file(path)


def test_rejects_nonstandard_json_constants(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"value":NaN}', encoding="utf-8")

    with pytest.raises(ManifestLoadError, match="numeric constant"):
        load_manifest_file(path)


def test_rejects_non_object_json_root(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ManifestLoadError, match="root"):
        load_manifest_file(path)


def test_rejects_invalid_utf8(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_bytes(b"\xff\xfe")

    with pytest.raises(ManifestLoadError, match="UTF-8"):
        load_manifest_file(path)


def test_rejects_utf8_bom(tmp_path):
    path = _write_payload(tmp_path / "manifest.json")
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())

    with pytest.raises(ManifestLoadError, match="BOM"):
        load_manifest_file(path)


def test_rejects_schema_invalid_manifest(tmp_path):
    payload = valid_payload()
    payload["schema_version"] = 999
    path = _write_payload(tmp_path / "manifest.json", payload)

    with pytest.raises(ManifestLoadError, match="schema validation"):
        load_manifest_file(path)


def test_default_size_limit_is_one_mib():
    assert DEFAULT_MAX_MANIFEST_BYTES == 1024 * 1024


def test_rejects_nul_in_path():
    with pytest.raises(ManifestLoadError, match="NUL"):
        load_manifest_file("/tmp/manifest\x00.json")


def test_rejects_bytes_path():
    with pytest.raises(ManifestLoadError, match="nonempty string"):
        load_manifest_file(b"/tmp/manifest.json")


def test_loads_valid_manifest_bytes():
    raw_data = json.dumps(valid_payload()).encode("utf-8")
    result = load_manifest_bytes(raw_data, now=TEST_NOW)
    assert result.schema_version == 1
    assert result.target.environment == "testing"


@pytest.mark.parametrize(
    "value",
    ["{}", bytearray(b"{}"), memoryview(b"{}")],
)
def test_bytes_loader_rejects_non_bytes_input(value):
    with pytest.raises(ManifestLoadError, match="must be bytes"):
        load_manifest_bytes(value)


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_bytes_loader_rejects_invalid_max_bytes(value):
    with pytest.raises(ManifestLoadError, match="max_bytes"):
        load_manifest_bytes(b"{}", max_bytes=value)


def test_bytes_loader_rejects_oversized_data():
    with pytest.raises(ManifestLoadError, match="size limit"):
        load_manifest_bytes(b" " * 129, max_bytes=128)


def test_bytes_loader_rejects_utf8_bom():
    raw = b"\xef\xbb\xbf" + json.dumps(
        valid_payload()
    ).encode("utf-8")
    with pytest.raises(ManifestLoadError, match="BOM"):
        load_manifest_bytes(raw, now=TEST_NOW)


def test_bytes_loader_rejects_invalid_utf8():
    with pytest.raises(ManifestLoadError, match="UTF-8"):
        load_manifest_bytes(b"\xff\xfe")


def test_bytes_loader_rejects_duplicate_json_keys():
    raw = b'{"schema_version":1,"schema_version":1}'
    with pytest.raises(ManifestLoadError, match="duplicate"):
        load_manifest_bytes(raw, now=TEST_NOW)


def test_bytes_loader_rejects_nonstandard_json_constants():
    with pytest.raises(ManifestLoadError, match="numeric constant"):
        load_manifest_bytes(b'{"value":NaN}', now=TEST_NOW)


def test_bytes_loader_rejects_non_object_json_root():
    with pytest.raises(ManifestLoadError, match="root"):
        load_manifest_bytes(b"[]", now=TEST_NOW)


def test_bytes_loader_rejects_malformed_json():
    with pytest.raises(ManifestLoadError, match="JSON is invalid"):
        load_manifest_bytes(b'{"broken":', now=TEST_NOW)


def test_bytes_loader_rejects_invalid_manifest_schema():
    payload = valid_payload()
    payload["schema_version"] = 999
    raw = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestLoadError, match="schema validation"):
        load_manifest_bytes(raw, now=TEST_NOW)


def test_bytes_loader_rejects_manifest_before_issued_at():
    payload = valid_payload()
    payload["validity"]["issued_at"] = "2026-11-18T12:00:01Z"
    raw = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestLoadError, match="schema validation"):
        load_manifest_bytes(raw, now=TEST_NOW)


def test_bytes_loader_rejects_manifest_at_expiry():
    payload = valid_payload()
    payload["validity"]["expires_at"] = "2026-11-18T12:00:00Z"
    raw = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestLoadError, match="schema validation"):
        load_manifest_bytes(raw, now=TEST_NOW)
