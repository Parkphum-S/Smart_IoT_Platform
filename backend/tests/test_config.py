"""Unit tests for application configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_MIGRATION_DATABASE_URL = (
    "postgresql+asyncpg://migration_user:test_password@127.0.0.1:5432/test_db"
)


def test_migration_database_url_is_optional():
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
    )
    assert settings.trusted_origins == ["https://example.com"]
