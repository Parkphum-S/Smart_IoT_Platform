"""Runtime helper for safely executing asynchronous Alembic migrations."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


async def run_migrations_with_engine(
    configuration: dict[str, Any],
    database_url: str,
    database_role: str,
    migration_callback: Callable[[Connection], None],
) -> None:
    """Create an isolated migration engine and always dispose it."""
    engine_configuration = dict(configuration)
    engine_configuration["sqlalchemy.url"] = database_url

    connectable = async_engine_from_config(
        engine_configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.exec_driver_sql(
                f"SET ROLE {database_role}"
            )
            await connection.commit()
            await connection.run_sync(migration_callback)
    finally:
        await connectable.dispose()
