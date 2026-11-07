"""Unit tests for application configuration."""

import pytest
from pydantic import ValidationError

import app.core.config as config
from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("TRUSTED_ORIGINS", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def clear_settings_environment(monkeypatch):
    """Remove inherited settings that could affect dotenv tests."""
    for name in (
        "APP_ENV",
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "MIGRATION_DATABASE_ROLE",
        "API_V1_PREFIX",
        "DEBUG",
        "SECRET_KEY",
        "GATEWAY_ENCRYPTION_KEY",
        "GATEWAY_ENCRYPTION_KEYS",
        "GATEWAY_ENCRYPTION_KEY_VERSION",
        "TRUSTED_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_MIGRATION_DATABASE_URL = (
    "postgresql+asyncpg://migration_user:test_password@127.0.0.1:5432/test_db"
)


def test_migration_database_url_is_optional(monkeypatch):
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None, database_url=TEST_DATABASE_URL)
    assert settings.migration_database_url is None


def test_migration_database_url_accepts_separate_connection():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        migration_database_url=TEST_MIGRATION_DATABASE_URL,
    )
    assert str(settings.database_url) == TEST_DATABASE_URL
    assert str(settings.migration_database_url) == TEST_MIGRATION_DATABASE_URL


def test_session_settings_have_approved_defaults():
    settings = Settings(_env_file=None, database_url=TEST_DATABASE_URL)

    assert settings.session_absolute_lifetime_seconds == 604800
    assert settings.session_idle_timeout_seconds == 1800
    assert settings.session_activity_update_interval_seconds == 300


def test_session_settings_accept_custom_values():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        session_absolute_lifetime_seconds=86400,
        session_idle_timeout_seconds=900,
        session_activity_update_interval_seconds=120,
    )

    assert settings.session_absolute_lifetime_seconds == 86400
    assert settings.session_idle_timeout_seconds == 900
    assert settings.session_activity_update_interval_seconds == 120


@pytest.mark.parametrize(
    "overrides",
    [
        {"session_absolute_lifetime_seconds": 0},
        {"session_idle_timeout_seconds": 0},
        {"session_activity_update_interval_seconds": 0},
        {
            "session_absolute_lifetime_seconds": 1800,
            "session_idle_timeout_seconds": 1800,
        },
        {
            "session_idle_timeout_seconds": 300,
            "session_activity_update_interval_seconds": 300,
        },
    ],
)
def test_invalid_session_settings_are_rejected(overrides):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            **overrides,
        )


def test_trusted_origins_default_to_empty():
    settings = Settings(_env_file=None, database_url=TEST_DATABASE_URL)
    assert settings.trusted_origins == []


def test_trusted_origins_accept_valid_http_and_https_origins():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        trusted_origins=[
            "https://example.com",
            "http://localhost:5173",
        ],
    )
    assert settings.trusted_origins == [
        "https://example.com",
        "http://localhost:5173",
    ]


@pytest.mark.parametrize(
    "origin",
    [
        "ftp://example.com",
        "https://",
        "https://user:password@example.com",
        "https://example.com/path",
        "https://example.com/",
        "https://example.com?query=1",
        "https://example.com#fragment",
        "https://example.com:0",
        "https://example.com:99999",
        "https://example.com:invalid",
        "https://example.com extra",
    ],
)
def test_invalid_trusted_origins_are_rejected(origin):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            trusted_origins=[origin],
        )


def test_duplicate_trusted_origins_are_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            trusted_origins=[
                "https://example.com",
                "https://example.com",
            ],
        )


def test_production_requires_trusted_origins():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            app_env="production",
            debug=False,
            secret_key="x" * 32,
            trusted_origins=[],
        )


def test_production_accepts_valid_trusted_origins():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        app_env="production",
        debug=False,
        secret_key="x" * 32,
        trusted_origins=["https://example.com"],
        gateway_encryption_key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
    )
    assert settings.trusted_origins == ["https://example.com"]


# Gateway encryption settings tests

def test_gateway_encryption_key_is_optional_outside_production():
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        app_env="testing",
    )
    assert settings.gateway_encryption_key is None


def test_gateway_encryption_key_accepts_32_byte_base64_key():
    import base64

    encoded_key = base64.b64encode(bytes(range(32))).decode("ascii")
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        gateway_encryption_key=encoded_key,
    )

    assert settings.gateway_encryption_key is not None
    assert settings.gateway_encryption_key.get_secret_value() == encoded_key
    assert settings.gateway_encryption_key_version == "v1"


@pytest.mark.parametrize(
    "invalid_key",
    [
        "not-base64!",
        "c2hvcnQ=",
        "eA==",
    ],
)
def test_invalid_gateway_encryption_key_is_rejected(invalid_key):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            gateway_encryption_key=invalid_key,
        )


def test_production_requires_gateway_encryption_key():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            app_env="production",
            debug=False,
            secret_key="x" * 32,
            trusted_origins=["https://example.com"],
        )


def test_production_accepts_gateway_encryption_key():
    import base64

    encoded_key = base64.b64encode(bytes(range(32))).decode("ascii")
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        app_env="production",
        debug=False,
        secret_key="x" * 32,
        gateway_encryption_key=encoded_key,
        trusted_origins=["https://example.com"],
    )

    assert settings.gateway_encryption_key is not None


def test_invalid_gateway_encryption_key_version_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            gateway_encryption_key_version="../invalid",
        )

def test_gateway_encryption_keyring_accepts_multiple_versions():
    import base64

    key_v1 = base64.b64encode(bytes(range(32))).decode("ascii")
    key_v2 = base64.b64encode(bytes(reversed(range(32)))).decode("ascii")

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        gateway_encryption_keys={"v1": key_v1, "v2": key_v2},
        gateway_encryption_key_version="v2",
    )

    assert set(settings.gateway_encryption_keys) == {"v1", "v2"}
    assert settings.gateway_encryption_key_version == "v2"


def test_gateway_encryption_keyring_requires_active_version():
    import base64

    key_v1 = base64.b64encode(bytes(range(32))).decode("ascii")

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            gateway_encryption_keys={"v1": key_v1},
            gateway_encryption_key_version="v2",
        )


@pytest.mark.parametrize(
    "keys",
    [
        {"../invalid": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="},
        {"v1": "not-base64!"},
        {"v1": "c2hvcnQ="},
    ],
)
def test_invalid_gateway_encryption_keyring_is_rejected(keys):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            gateway_encryption_keys=keys,
        )


def test_production_accepts_gateway_encryption_keyring_without_legacy_key():
    import base64

    key_v1 = base64.b64encode(bytes(range(32))).decode("ascii")
    key_v2 = base64.b64encode(bytes(reversed(range(32)))).decode("ascii")

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        app_env="production",
        debug=False,
        secret_key="x" * 32,
        gateway_encryption_keys={"v1": key_v1, "v2": key_v2},
        gateway_encryption_key_version="v2",
        trusted_origins=["https://example.com"],
    )

    assert settings.gateway_encryption_key is None
    assert settings.gateway_encryption_key_version == "v2"


@pytest.mark.parametrize(
    "role",
    [
        "smart_iot_owner",
        "smart_iot_test_owner",
        "owner123",
        "_owner",
    ],
)
def test_valid_migration_database_roles_are_accepted(role):
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        migration_database_role=role,
    )

    assert settings.migration_database_role == role


@pytest.mark.parametrize(
    "role",
    [
        "Owner",
        "owner-role",
        "owner.role",
        "owner; DROP TABLE users",
        "owner role",
        "",
        "a" * 64,
    ],
)
def test_invalid_migration_database_roles_are_rejected(role):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            migration_database_role=role,
        )
def test_get_settings_uses_development_dotenv(tmp_path, monkeypatch):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("APP_ENV", "development")
    (tmp_path / ".env").write_text(
        f"APP_ENV=development\nDATABASE_URL={TEST_DATABASE_URL}\n"
        "API_V1_PREFIX=/development-env\n",
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.api_v1_prefix == "/development-env"


def test_get_settings_uses_integration_dotenv_only(tmp_path, monkeypatch):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("APP_ENV", "testing")
    (tmp_path / ".env").write_text(
        f"APP_ENV=production\nDATABASE_URL={TEST_DATABASE_URL}\n"
        "API_V1_PREFIX=/production-env\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.integration").write_text(
        f"APP_ENV=testing\nDATABASE_URL={TEST_DATABASE_URL}\n"
        f"MIGRATION_DATABASE_URL={TEST_MIGRATION_DATABASE_URL}\n"
        "MIGRATION_DATABASE_ROLE=smart_iot_test_owner\n"
        "API_V1_PREFIX=/integration-env\n",
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.app_env == "testing"
    assert settings.api_v1_prefix == "/integration-env"
    assert str(settings.migration_database_url) == TEST_MIGRATION_DATABASE_URL
    assert settings.migration_database_role == "smart_iot_test_owner"


def test_get_settings_uses_production_dotenv(tmp_path, monkeypatch):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("APP_ENV", "production")
    (tmp_path / ".env").write_text(
        f"APP_ENV=production\nDATABASE_URL={TEST_DATABASE_URL}\n"
        "DEBUG=false\n"
        f"SECRET_KEY={'x' * 32}\n"
        "GATEWAY_ENCRYPTION_KEY="
        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=\n"
        'TRUSTED_ORIGINS=["https://example.com"]\n'
        "API_V1_PREFIX=/production-env\n",
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.app_env == "production"
    assert settings.api_v1_prefix == "/production-env"


def test_get_settings_process_environment_overrides_dotenv(
    tmp_path, monkeypatch
):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_V1_PREFIX", "/process-env")
    (tmp_path / ".env").write_text(
        f"DATABASE_URL={TEST_DATABASE_URL}\n"
        "API_V1_PREFIX=/dotenv\n",
        encoding="utf-8",
    )

    assert get_settings().api_v1_prefix == "/process-env"


def test_get_settings_without_app_env_does_not_load_dotenv(
    tmp_path, monkeypatch
):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    (tmp_path / ".env").write_text(
        f"DATABASE_URL={TEST_DATABASE_URL}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        get_settings()


def test_direct_settings_does_not_load_dotenv_by_default(
    tmp_path, monkeypatch
):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    (tmp_path / ".env").write_text(
        f"DATABASE_URL={TEST_DATABASE_URL}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        Settings()


def test_get_settings_rejects_invalid_app_env(monkeypatch):
    clear_settings_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "unknown")

    with pytest.raises(ValueError, match="APP_ENV must be"):
        get_settings()


def test_get_settings_cache_clear_reloads_dotenv(tmp_path, monkeypatch):
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("APP_ENV", "development")
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"DATABASE_URL={TEST_DATABASE_URL}\n"
        "API_V1_PREFIX=/first\n",
        encoding="utf-8",
    )

    first = get_settings()
    env_file.write_text(
        f"DATABASE_URL={TEST_DATABASE_URL}\n"
        "API_V1_PREFIX=/second\n",
        encoding="utf-8",
    )
    assert get_settings() is first

    get_settings.cache_clear()
    second = get_settings()

    assert second.api_v1_prefix == "/second"
