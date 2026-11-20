"""Shared integration database isolation guard."""

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


EXPECTED_DATABASE = "smart_iot_integration_test"
EXPECTED_APP_ROLE = "smart_iot_test_app"
EXPECTED_FIXTURE_ROLE = "smart_iot_test_fixture"
EXPECTED_MIGRATOR_ROLE = "smart_iot_test_migrator"
EXPECTED_OWNER_ROLE = "smart_iot_test_owner"


def validate_test_database_settings(settings) -> None:
    """Enforce database endpoint isolation across all environments."""
    errors = []

    test_roles = {
        EXPECTED_APP_ROLE,
        EXPECTED_FIXTURE_ROLE,
        EXPECTED_MIGRATOR_ROLE,
        EXPECTED_OWNER_ROLE,
    }

    targets = (
        ("DATABASE_URL", settings.database_url, EXPECTED_APP_ROLE),
        ("FIXTURE_DATABASE_URL", settings.fixture_database_url, EXPECTED_FIXTURE_ROLE),
        ("MIGRATION_DATABASE_URL", settings.migration_database_url, EXPECTED_MIGRATOR_ROLE),
    )

    parsed_targets = []
    is_testing = settings.app_env == "testing"

    for label, url, expected_role in targets:
        if url is None:
            if is_testing:
                errors.append(f"{label} must be configured")
            continue

        try:
            parsed = make_url(str(url))
        except (ArgumentError, TypeError, ValueError):
            errors.append(f"{label} must be a valid database URL")
            continue

        parsed_targets.append((label, parsed, expected_role))

        is_test_target = (
            parsed.database == EXPECTED_DATABASE
            or parsed.username in test_roles
        )

        if not is_testing:
            if is_test_target:
                errors.append(
                    f"{label} must not target integration test resources"
                )
            continue

        if parsed.drivername != "postgresql+asyncpg":
            errors.append(
                f"{label} must use the supported PostgreSQL async driver"
            )

        if not parsed.host:
            errors.append(f"{label} must specify a database host")

        if parsed.database != EXPECTED_DATABASE:
            errors.append(
                f"{label} must target the integration test database"
            )

        if parsed.username != expected_role:
            errors.append(
                f"{label} must use its approved integration role"
            )

    if is_testing:
        if settings.migration_database_role != EXPECTED_OWNER_ROLE:
            errors.append(
                "MIGRATION_DATABASE_ROLE must be the integration owner role"
            )

        endpoints = {
            (parsed.host.lower(), parsed.port or 5432)
            for _, parsed, _ in parsed_targets
            if parsed.host
        }

        if len(parsed_targets) == 3 and len(endpoints) != 1:
            errors.append(
                "Integration database URLs must use the same host and port"
            )
    elif settings.migration_database_role in test_roles:
        errors.append(
            "MIGRATION_DATABASE_ROLE must not use an integration test role"
        )

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(
            "Database Guard blocked operation:\n" + details
        )
