"""Alembic environment for asynchronous SQLAlchemy migrations."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.infrastructure.database.base import Base
from app.modules.users import models as users_models
from app.modules.devices import models as devices_models
from app.modules.telemetry import models as telemetry_models
from app.modules.monitoring import models as monitoring_models
from app.modules.automation import models as automation_models


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Get the database URL from centralized application settings."""
    return str(get_settings().database_url)


def get_migration_database_url() -> str:
    """Get and validate the dedicated database URL used by Alembic."""
    settings = get_settings()
    url = settings.migration_database_url

    if url is None:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL must be configured before running migrations."
        )

    parsed_url = make_url(str(url))

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

    return str(url)


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
    """Create an async engine and run migrations."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_migration_database_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.exec_driver_sql(
            f"SET ROLE {get_migration_database_role()}"
        )
        await connection.commit()
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations using an asynchronous database connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
