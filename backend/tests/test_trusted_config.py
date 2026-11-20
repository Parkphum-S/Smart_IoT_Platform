"""Tests for the local trusted orchestrator configuration contract."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.infrastructure.database.trust.trusted_config import (
    DEFAULT_MAX_MANIFEST_BYTES,
    DEFAULT_MAX_REGISTRY_BYTES,
    DEFAULT_MAX_SIGNATURE_BYTES,
    TrustedConfigurationError,
    TrustedOrchestratorConfig,
)


@pytest.fixture
def valid_config():
    return {
        "bundle_root": "/etc/smart-iot-trust",
        "selected_key_id": "integration-key-01",
        "expected_environment": "testing",
    }


@pytest.fixture
def valid_environment():
    return {
        "TRUSTED_BUNDLE_ROOT": "/etc/smart-iot-trust",
        "TRUSTED_KEY_ID": "integration-key-01",
    }


def test_valid_configuration(valid_config):
    config = TrustedOrchestratorConfig.model_validate(valid_config)

    assert config.bundle_root == "/etc/smart-iot-trust"
    assert config.expected_environment == "testing"
    assert config.selected_key_id == "integration-key-01"


def test_default_file_limits(valid_config):
    config = TrustedOrchestratorConfig.model_validate(valid_config)

    assert config.max_manifest_bytes == DEFAULT_MAX_MANIFEST_BYTES
    assert config.max_signature_bytes == DEFAULT_MAX_SIGNATURE_BYTES
    assert config.max_registry_bytes == DEFAULT_MAX_REGISTRY_BYTES


@pytest.mark.parametrize(
    "path",
    [
        "relative/trust",
        "/tmp/../trust",
        "/tmp//trust",
        "//etc/trust",
        "/",
        "/tmp/",
    ],
)
def test_rejects_invalid_bundle_root(valid_config, path):
    valid_config["bundle_root"] = path

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


def test_rejects_nul_in_bundle_root(valid_config):
    valid_config["bundle_root"] = "/tmp/trust\x00root"

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


@pytest.mark.parametrize(
    "key_id",
    ["", "../key", "key id", "key/01", "x" * 129],
)
def test_rejects_invalid_key_id(valid_config, key_id):
    valid_config["selected_key_id"] = key_id

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


def test_rejects_non_testing_environment(valid_config):
    valid_config["expected_environment"] = "production"

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("max_manifest_bytes", DEFAULT_MAX_MANIFEST_BYTES),
        ("max_signature_bytes", DEFAULT_MAX_SIGNATURE_BYTES),
        ("max_registry_bytes", DEFAULT_MAX_REGISTRY_BYTES),
    ],
)
def test_rejects_file_limit_above_hard_cap(valid_config, field, maximum):
    valid_config[field] = maximum + 1

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


@pytest.mark.parametrize(
    "value",
    [0, -1, True, "1024"],
)
def test_rejects_invalid_manifest_size(valid_config, value):
    valid_config["max_manifest_bytes"] = value

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


def test_configuration_is_immutable(valid_config):
    config = TrustedOrchestratorConfig.model_validate(valid_config)

    with pytest.raises(ValidationError):
        config.selected_key_id = "replacement"


def test_rejects_unknown_fields(valid_config):
    valid_config["unexpected"] = "value"

    with pytest.raises(ValidationError):
        TrustedOrchestratorConfig.model_validate(valid_config)


def test_loads_configuration_from_explicit_environment(
    valid_environment,
):
    settings = SimpleNamespace(app_env="testing")

    config = TrustedOrchestratorConfig.from_environment(
        settings,
        environ=valid_environment,
    )

    assert config.bundle_root == "/etc/smart-iot-trust"
    assert config.expected_environment == "testing"
    assert config.selected_key_id == "integration-key-01"


def test_rejects_missing_configuration(valid_environment):
    settings = SimpleNamespace(app_env="testing")
    valid_environment.pop("TRUSTED_KEY_ID")

    with pytest.raises(TrustedConfigurationError):
        TrustedOrchestratorConfig.from_environment(
            settings,
            environ=valid_environment,
        )


def test_rejects_production_environment(valid_environment):
    settings = SimpleNamespace(app_env="production")

    with pytest.raises(TrustedConfigurationError):
        TrustedOrchestratorConfig.from_environment(
            settings,
            environ=valid_environment,
        )


def test_rejects_invalid_size_environment_variable(valid_environment):
    settings = SimpleNamespace(app_env="testing")
    valid_environment["TRUSTED_MAX_MANIFEST_BYTES"] = "1MiB"

    with pytest.raises(TrustedConfigurationError):
        TrustedOrchestratorConfig.from_environment(
            settings,
            environ=valid_environment,
        )


def test_accepts_custom_size_within_limit(valid_environment):
    settings = SimpleNamespace(app_env="testing")
    valid_environment["TRUSTED_MAX_MANIFEST_BYTES"] = "4096"

    config = TrustedOrchestratorConfig.from_environment(
        settings,
        environ=valid_environment,
    )

    assert config.max_manifest_bytes == 4096


def test_does_not_mutate_environment_mapping(valid_environment):
    settings = SimpleNamespace(app_env="testing")
    original = valid_environment.copy()

    TrustedOrchestratorConfig.from_environment(
        settings,
        environ=valid_environment,
    )

    assert valid_environment == original
