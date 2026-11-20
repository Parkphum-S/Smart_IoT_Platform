"""Strict local configuration contract for the trusted manifest orchestrator."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)


DEFAULT_MAX_MANIFEST_BYTES = 1024 * 1024
DEFAULT_MAX_SIGNATURE_BYTES = 16 * 1024
DEFAULT_MAX_REGISTRY_BYTES = 256 * 1024

MAX_MANIFEST_BYTES_LIMIT = DEFAULT_MAX_MANIFEST_BYTES
MAX_SIGNATURE_BYTES_LIMIT = DEFAULT_MAX_SIGNATURE_BYTES
MAX_REGISTRY_BYTES_LIMIT = DEFAULT_MAX_REGISTRY_BYTES

_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TrustedConfigurationError(ValueError):
    """Raised when trusted orchestrator configuration is unavailable."""


class TrustedOrchestratorConfig(BaseModel):
    """Immutable configuration for local trusted-manifest verification.

    Values must come from an independently trusted configuration source.
    This model does not load files, access databases, or verify signatures.
    """

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    bundle_root: StrictStr
    selected_key_id: StrictStr
    expected_environment: Literal["testing"]

    max_manifest_bytes: StrictInt = Field(
        default=DEFAULT_MAX_MANIFEST_BYTES,
        ge=1,
        le=MAX_MANIFEST_BYTES_LIMIT,
    )
    max_signature_bytes: StrictInt = Field(
        default=DEFAULT_MAX_SIGNATURE_BYTES,
        ge=1,
        le=MAX_SIGNATURE_BYTES_LIMIT,
    )
    max_registry_bytes: StrictInt = Field(
        default=DEFAULT_MAX_REGISTRY_BYTES,
        ge=1,
        le=MAX_REGISTRY_BYTES_LIMIT,
    )

    @field_validator("bundle_root")
    @classmethod
    def validate_bundle_root(cls, value: str) -> str:
        if not value or "\x00" in value:
            raise ValueError(
                "trusted bundle root must be nonempty and valid"
            )

        path = PurePosixPath(value)

        if not path.is_absolute():
            raise ValueError("trusted bundle root must be absolute")

        components = value.split("/")[1:]
        if any(part in {"", ".", ".."} for part in components):
            raise ValueError(
                "trusted bundle root contains invalid components"
            )

        if value == "/" or value.endswith("/"):
            raise ValueError(
                "trusted bundle root must identify a directory"
            )

        return value

    @field_validator("selected_key_id")
    @classmethod
    def validate_selected_key_id(cls, value: str) -> str:
        if _KEY_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("selected trusted key ID is invalid")
        return value

    @classmethod
    def from_environment(
        cls,
        settings: object,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "TrustedOrchestratorConfig":
        """Build configuration from explicit local environment variables.

        Application environment is obtained from the existing Settings
        object. Trust-specific values are read only from the supplied
        mapping or process environment.
        """
        source = os.environ if environ is None else environ

        try:
            app_environment = getattr(settings, "app_env")
        except AttributeError as exc:
            raise TrustedConfigurationError(
                "application environment is unavailable"
            ) from exc

        if app_environment != "testing":
            raise TrustedConfigurationError(
                "trusted manifest execution is restricted to testing"
            )

        required = (
            "TRUSTED_BUNDLE_ROOT",
            "TRUSTED_KEY_ID",
        )

        missing = [
            name for name in required
            if name not in source or not source[name]
        ]

        if missing:
            raise TrustedConfigurationError(
                "required trusted configuration is missing: "
                + ", ".join(missing)
            )

        def read_limit(name: str, default: int) -> int:
            raw = source.get(name)

            if raw is None:
                return default

            if (
                not isinstance(raw, str)
                or re.fullmatch(r"[0-9]+", raw) is None
            ):
                raise TrustedConfigurationError(
                    f"{name} must be a positive decimal integer"
                )

            return int(raw)

        try:
            return cls.model_validate(
                {
                    "bundle_root": source["TRUSTED_BUNDLE_ROOT"],
                    "selected_key_id": source["TRUSTED_KEY_ID"],
                    "expected_environment": app_environment,
                    "max_manifest_bytes": read_limit(
                        "TRUSTED_MAX_MANIFEST_BYTES",
                        DEFAULT_MAX_MANIFEST_BYTES,
                    ),
                    "max_signature_bytes": read_limit(
                        "TRUSTED_MAX_SIGNATURE_BYTES",
                        DEFAULT_MAX_SIGNATURE_BYTES,
                    ),
                    "max_registry_bytes": read_limit(
                        "TRUSTED_MAX_REGISTRY_BYTES",
                        DEFAULT_MAX_REGISTRY_BYTES,
                    ),
                }
            )
        except (ValueError, TypeError) as exc:
            raise TrustedConfigurationError(
                "trusted orchestrator configuration is invalid"
            ) from exc
