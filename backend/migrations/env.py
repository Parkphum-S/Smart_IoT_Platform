"""Alembic environment for asynchronous SQLAlchemy migrations."""

import asyncio
import os
import stat
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection, make_url

from app.infrastructure.database.migration_runner import (
    run_migrations_with_engine,
)

from app.core.config import get_settings
from app.infrastructure.database.base import Base
from app.modules.users import models as users_models
from app.modules.devices import models as devices_models
from app.modules.telemetry import models as telemetry_models
from app.modules.monitoring import models as monitoring_models
from app.modules.automation import models as automation_models
from app.integrations.mqtt import models as mqtt_models


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Get the database URL from centralized application settings."""
    return str(get_settings().database_url)


def _read_migration_password_file(path_value: str) -> str:
    """Read a private migration credential without following symlinks."""
    if not os.path.isabs(path_value):
        raise RuntimeError("Migration credential path must be absolute.")

    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError("Secure no-follow file access is unavailable.")

    fd = os.open(path_value, os.O_RDONLY | nofollow)
    try:
        metadata = os.fstat(fd)

        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("Migration credential must be a regular file.")

        if metadata.st_uid != os.getuid():
            raise RuntimeError("Migration credential owner is invalid.")

        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise RuntimeError("Migration credential permissions are too broad.")

        if not 1 <= metadata.st_size <= 4096:
            raise RuntimeError("Migration credential size is invalid.")

        raw = os.read(fd, metadata.st_size + 1)
        if len(raw) != metadata.st_size:
            raise RuntimeError("Migration credential changed while reading.")
    finally:
        os.close(fd)

    try:
        password = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Migration credential encoding is invalid.") from exc

    if not password or any(char.isspace() for char in password):
        raise RuntimeError("Migration credential content is invalid.")

    return password


def get_migration_database_url() -> str:
    """Get and validate the dedicated database URL used by Alembic."""
    settings = get_settings()
    url = settings.migration_database_url

    if url is not None:
        parsed_url = make_url(str(url))

    elif settings.app_env == "production":
        credential_path = os.environ.get(
            "MIGRATION_DATABASE_PASSWORD_FILE"
        )
        if not credential_path:
            raise RuntimeError(
                "MIGRATION_DATABASE_PASSWORD_FILE must be configured."
            )

        password = _read_migration_password_file(credential_path)

        parsed_url = make_url(str(settings.database_url)).set(
            username="smart_iot_migrator",
            password=password,
        )

    else:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL must be configured before running migrations."
        )

    if settings.app_env == "testing":
        if (
            parsed_url.database != "smart_iot_integration_test"
            or parsed_url.username != "smart_iot_test_migrator"
            or settings.migration_database_role != "smart_iot_test_owner"
        ):
            raise RuntimeError(
                "Database Guard: migration target does not match "
                "the approved integration test database configuration."
            )

    test_database_roles = {
        "smart_iot_test_owner",
        "smart_iot_test_migrator",
        "smart_iot_test_app",
    }

    if (
        settings.migration_database_role in test_database_roles
        and settings.app_env != "testing"
    ):
        raise RuntimeError(
            "Database Guard: test database roles require APP_ENV=testing."
        )

    if settings.app_env == "production":
        if (
            parsed_url.database != "smart_iot"
            or parsed_url.username != "smart_iot_migrator"
            or settings.migration_database_role != "smart_iot_owner"
        ):
            raise RuntimeError(
                "Database Guard: production migration target is not approved."
            )

    return parsed_url.render_as_string(hide_password=False)



def get_migration_database_role() -> str:
    """Get the database role used by Alembic after connecting."""
    return get_settings().migration_database_role


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=get_migration_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.execute(f"SET ROLE {get_migration_database_role()}")
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations using a synchronous connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the dedicated migration engine."""
    configuration = config.get_section(config.config_ini_section) or {}

    await run_migrations_with_engine(
        configuration=configuration,
        database_url=get_migration_database_url(),
        database_role=get_migration_database_role(),
        migration_callback=do_run_migrations,
    )


def run_migrations_online() -> None:
    """Run migrations using a caller-owned or dedicated connection."""
    connection = config.attributes.get("connection")

    if connection is not None:
        if not isinstance(connection, Connection):
            raise TypeError(
                "Alembic caller-owned connection must be a "
                "synchronous SQLAlchemy Connection."
            )

        if connection.closed or connection.invalidated:
            raise RuntimeError(
                "Alembic caller-owned connection is unavailable."
            )

        do_run_migrations(connection)
        return

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
