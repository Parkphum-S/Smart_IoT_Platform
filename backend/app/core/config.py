"""Central application configuration using Pydantic Settings."""

import base64
import binascii
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Smart IoT Platform"
    app_version: str = "0.1.0"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    api_v1_prefix: str = "/api/v1"

    database_url: PostgresDsn
    migration_database_url: PostgresDsn | None = None
    migration_database_role: str = "smart_iot_owner"

    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=5, ge=0, le=20)
    db_pool_timeout: int = Field(default=30, ge=1, le=120)

    session_absolute_lifetime_seconds: int = Field(default=604800, ge=1)
    session_idle_timeout_seconds: int = Field(default=1800, ge=1)
    session_activity_update_interval_seconds: int = Field(default=300, ge=1)

    secret_key: SecretStr | None = Field(default=None)
    gateway_encryption_key: SecretStr | None = Field(default=None)
    gateway_encryption_keys: dict[str, SecretStr] = Field(default_factory=dict)
    gateway_encryption_key_version: str = Field(
        default="v1", min_length=1, max_length=40
    )
    trusted_origins: list[str] = Field(default_factory=list)

    @field_validator("gateway_encryption_key")
    @classmethod
    def validate_gateway_encryption_key(
        cls, value: SecretStr | None
    ) -> SecretStr | None:
        """Require a Base64-encoded 32-byte AES-256 key."""
        if value is None:
            return None

        try:
            decoded = base64.b64decode(
                value.get_secret_value(),
                validate=True,
            )
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "GATEWAY_ENCRYPTION_KEY must be valid Base64."
            ) from exc

        if len(decoded) != 32:
            raise ValueError(
                "GATEWAY_ENCRYPTION_KEY must decode to exactly 32 bytes."
            )

        return value


    @field_validator("gateway_encryption_keys")
    @classmethod
    def validate_gateway_encryption_keys(
        cls, values: dict[str, SecretStr]
    ) -> dict[str, SecretStr]:
        """Validate every versioned Base64-encoded AES-256 key."""
        decoded_keys: set[bytes] = set()

        for version, value in values.items():
            if (
                not isinstance(version, str)
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", version)
                is None
            ):
                raise ValueError("Gateway encryption key version is invalid.")

            if not isinstance(value, SecretStr):
                raise ValueError("Gateway encryption keys must be secret values.")

            try:
                decoded = base64.b64decode(
                    value.get_secret_value(),
                    validate=True,
                )
            except (binascii.Error, ValueError) as exc:
                raise ValueError(
                    "Gateway encryption keys must be valid Base64."
                ) from exc

            if len(decoded) != 32:
                raise ValueError(
                    "Gateway encryption keys must decode to exactly 32 bytes."
                )

            if decoded in decoded_keys:
                raise ValueError(
                    "Gateway encryption key material must be unique across versions."
                )

            decoded_keys.add(decoded)

        return values

    @field_validator("gateway_encryption_key_version")
    @classmethod
    def validate_gateway_encryption_key_version(cls, value: str) -> str:
        """Validate the encryption key version identifier."""
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", value) is None:
            raise ValueError("Gateway encryption key version is invalid.")
        return value

    @field_validator("migration_database_role")
    @classmethod
    def validate_migration_database_role(cls, role: str) -> str:
        """Accept only safe, lowercase PostgreSQL role identifiers."""
        if re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", role) is None:
            raise ValueError("Migration database role is invalid.")
        return role

    @field_validator("trusted_origins")
    @classmethod
    def validate_trusted_origins(cls, origins: list[str]) -> list[str]:
        """Accept only unique, canonical HTTP(S) origins without paths."""
        validated: list[str] = []

        for origin in origins:
            if (
                not isinstance(origin, str)
                or not origin
                or any(character.isspace() for character in origin)
            ):
                raise ValueError(
                    "Trusted origins must be non-empty URLs without whitespace."
                )

            try:
                parsed = urlsplit(origin)
                port = parsed.port
            except ValueError as exc:
                raise ValueError("Trusted origin contains an invalid port or URL.") from exc

            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or origin != f"{parsed.scheme}://{parsed.netloc}"
            ):
                raise ValueError(
                    "Trusted origins must be canonical HTTP(S) origins "
                    "without credentials, paths, queries, or fragments."
                )

            if port is not None and not 1 <= port <= 65535:
                raise ValueError("Trusted origin port must be between 1 and 65535.")

            if origin in validated:
                raise ValueError("Trusted origins must not contain duplicates.")

            validated.append(origin)

        return validated

    @model_validator(mode="after")
    def validate_keyring_settings(self) -> "Settings":
        """Ensure the active version exists in a configured keyring."""
        if self.gateway_encryption_keys and (
            self.gateway_encryption_key_version not in self.gateway_encryption_keys
        ):
            raise ValueError(
                "Active gateway encryption key version is missing from keyring."
            )
        return self

    @model_validator(mode="after")
    def validate_session_settings(self) -> "Settings":
        """Ensure session lifetime settings are logically consistent."""
        if self.session_idle_timeout_seconds >= self.session_absolute_lifetime_seconds:
            raise ValueError("Session idle timeout must be less than absolute lifetime.")

        if self.session_activity_update_interval_seconds >= self.session_idle_timeout_seconds:
            raise ValueError("Session activity update interval must be less than idle timeout.")

        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Enforce minimum security requirements in production."""
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production.")

            if self.secret_key is None:
                raise ValueError("SECRET_KEY is required in production.")

            if len(self.secret_key.get_secret_value()) < 32:
                raise ValueError(
                    "SECRET_KEY must contain at least 32 characters in production."
                )
            if (
                self.gateway_encryption_key is None
                and not self.gateway_encryption_keys
            ):
                raise ValueError(
                    "A gateway encryption key or keyring is required in production."
                )

            if not self.trusted_origins:
                raise ValueError(
                    "TRUSTED_ORIGINS must contain at least one origin in production."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings using an explicitly selected environment file."""
    app_env = os.environ.get("APP_ENV")

    if app_env is None:
        env_file = None
    elif app_env in {"development", "production"}:
        env_file = BACKEND_DIR / ".env"
    elif app_env == "testing":
        env_file = BACKEND_DIR / ".env.integration"
    else:
        raise ValueError(
            "APP_ENV must be development, testing, or production."
        )

    return Settings(_env_file=env_file)
