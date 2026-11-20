"""Strict schema validation for the local Integration Target manifest."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


_ROLE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_SYSTEM_ID_PATTERN = re.compile(r"^[0-9]{1,32}$")


class StrictManifestModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )


class TargetIdentity(StrictManifestModel):
    target_id: StrictStr
    environment: Literal["testing"]
    manifest_version: StrictInt

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if not value or value != value.strip() or len(value) > 128:
            raise ValueError("invalid target_id")
        return value

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value < 1:
            raise ValueError("manifest_version must be positive")
        return value


class ConnectionIdentity(StrictManifestModel):
    database: StrictStr
    hostname: StrictStr
    port: StrictInt
    tls_server_name: StrictStr | None

    @field_validator("database")
    @classmethod
    def validate_database(cls, value: str) -> str:
        if value != "smart_iot_integration_test":
            raise ValueError("untrusted target database")
        return value

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("untrusted target hostname")
        return value

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if value != 5432:
            raise ValueError("untrusted target port")
        return value

    @field_validator("tls_server_name")
    @classmethod
    def validate_tls_server_name(
        cls, value: str | None
    ) -> str | None:
        if value is not None and (
            not value or value != value.strip() or len(value) > 253
        ):
            raise ValueError("invalid tls_server_name")
        return value


class ClusterIdentity(StrictManifestModel):
    postgresql_major: StrictInt
    system_identifier: StrictStr
    data_directory: StrictStr
    instance_identity: StrictStr
    is_standby: StrictBool

    @field_validator("postgresql_major")
    @classmethod
    def validate_postgresql_major(cls, value: int) -> int:
        if value < 1:
            raise ValueError("invalid PostgreSQL major version")
        return value

    @field_validator("system_identifier")
    @classmethod
    def validate_system_identifier(cls, value: str) -> str:
        if not _SYSTEM_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid system_identifier")
        return value

    @field_validator("data_directory")
    @classmethod
    def validate_data_directory(cls, value: str) -> str:
        if (
            not value.startswith("/")
            or value == "/"
            or "\x00" in value
            or ".." in value.split("/")
        ):
            raise ValueError("invalid data_directory")
        return value

    @field_validator("instance_identity")
    @classmethod
    def validate_instance_identity(cls, value: str) -> str:
        if not value or value != value.strip() or len(value) > 256:
            raise ValueError("invalid instance_identity")
        return value

    @field_validator("is_standby")
    @classmethod
    def reject_standby(cls, value: bool) -> bool:
        if value:
            raise ValueError("standby targets are not authorized")
        return value


class AuthorizationIdentity(StrictManifestModel):
    login_role: StrictStr
    effective_role: StrictStr
    allowed_operations: tuple[
        Literal["migration", "fixture", "application"], ...
    ]

    @field_validator("allowed_operations", mode="before")
    @classmethod
    def freeze_operations_input(cls, value: object) -> tuple:
        if type(value) is list:
            return tuple(value)
        if type(value) is tuple:
            return value
        raise ValueError("allowed_operations must be an array")

    @field_validator("login_role", "effective_role")
    @classmethod
    def validate_role_name(cls, value: str) -> str:
        if not _ROLE_PATTERN.fullmatch(value):
            raise ValueError("invalid database role name")
        return value

    @field_validator("allowed_operations")
    @classmethod
    def validate_operations(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("operations must be nonempty and unique")
        if value != ("migration",):
            raise ValueError("this manifest authorizes migration only")
        return value

    @model_validator(mode="after")
    def validate_roles(self) -> "AuthorizationIdentity":
        if self.login_role != "smart_iot_test_migrator":
            raise ValueError("untrusted migration login role")
        if self.effective_role != "smart_iot_test_owner":
            raise ValueError("untrusted effective role")
        return self


class IsolationIdentity(StrictManifestModel):
    level: Literal["database"]
    shared_cluster_with_production: StrictBool
    production_database: StrictStr

    @model_validator(mode="after")
    def validate_isolation(self) -> "IsolationIdentity":
        if self.shared_cluster_with_production is not True:
            raise ValueError("shared-cluster boundary must be explicit")
        if self.production_database != "smart_iot":
            raise ValueError("unexpected production database identity")
        return self


class ManifestValidity(StrictManifestModel):
    issued_at: StrictStr
    expires_at: StrictStr

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("invalid timestamp")

        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError("timestamp must be ISO 8601") from exc

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timestamp must include timezone")
        return value

    @model_validator(mode="after")
    def validate_validity_window(self) -> "ManifestValidity":
        issued = datetime.fromisoformat(
            self.issued_at.replace("Z", "+00:00")
        )
        expires = datetime.fromisoformat(
            self.expires_at.replace("Z", "+00:00")
        )
        if expires <= issued:
            raise ValueError("expires_at must follow issued_at")
        return self


class TrustedManifestPayload(StrictManifestModel):
    schema_version: StrictInt
    target: TargetIdentity
    connection: ConnectionIdentity
    cluster: ClusterIdentity
    authorization: AuthorizationIdentity
    isolation: IsolationIdentity
    validity: ManifestValidity

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("unsupported manifest schema version")
        return value


def validate_manifest_payload(
    payload: object,
    *,
    now: datetime | None = None,
) -> TrustedManifestPayload:
    """Validate schema and current validity without trusting the signature."""
    if not isinstance(payload, dict):
        raise ValueError("manifest payload must be a JSON object")

    manifest = TrustedManifestPayload.model_validate(payload)

    if now is None:
        now = datetime.now(timezone.utc)

    if not isinstance(now, datetime):
        raise ValueError("validation time must be a datetime")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("validation time must include timezone")

    issued = datetime.fromisoformat(
        manifest.validity.issued_at.replace("Z", "+00:00")
    )
    expires = datetime.fromisoformat(
        manifest.validity.expires_at.replace("Z", "+00:00")
    )

    if now < issued:
        raise ValueError("manifest is not yet valid")
    if now >= expires:
        raise ValueError("manifest has expired")

    return manifest
