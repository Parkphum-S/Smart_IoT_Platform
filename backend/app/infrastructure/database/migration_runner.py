"""Runtime helper for safely executing asynchronous Alembic migrations."""

from collections.abc import Callable
from pathlib import Path
import re
from typing import Any

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    async_engine_from_config,
)


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



async def run_migrations_with_connection(
    connection: AsyncConnection,
    database_role: str,
    migration_callback: Callable[[Connection], None],
) -> None:
    """Run migrations using a caller-owned connection and transaction."""
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", database_role):
        raise ValueError("Migration database role is invalid.")

    if connection.closed or connection.invalidated:
        raise RuntimeError("Migration connection is unavailable.")

    await connection.exec_driver_sql(f"SET ROLE {database_role}")
    try:
        await connection.run_sync(migration_callback)
    except BaseException:
        if not connection.closed and not connection.invalidated:
            if connection.in_transaction():
                await connection.rollback()
            await connection.exec_driver_sql("RESET ROLE")
            await connection.commit()
        raise
    else:
        if not connection.closed and not connection.invalidated:
            await connection.exec_driver_sql("RESET ROLE")
            await connection.commit()

async def read_alembic_current_heads(
    connection: AsyncConnection,
    database_role: str,
) -> tuple[str, ...]:
    """Read Alembic current heads using the caller-owned connection."""

    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", database_role):
        raise ValueError("Migration database role is invalid.")

    if connection.closed or connection.invalidated:
        raise RuntimeError("Migration connection is unavailable.")

    await connection.exec_driver_sql(f"SET ROLE {database_role}")
    await connection.commit()

    def read_heads(sync_connection: Connection) -> tuple[str, ...]:
        from alembic.runtime.migration import MigrationContext

        if sync_connection.closed or sync_connection.invalidated:
            raise RuntimeError("Alembic revision connection is unavailable.")

        migration_context = MigrationContext.configure(
            connection=sync_connection,
        )
        return tuple(migration_context.get_current_heads())

    try:
        heads = await connection.run_sync(read_heads)
    except BaseException:
        if not connection.closed and not connection.invalidated:
            if connection.in_transaction():
                await connection.rollback()

            try:
                await connection.exec_driver_sql("RESET ROLE")
                await connection.commit()
            except BaseException:
                await connection.invalidate()
        raise
    else:
        try:
            await connection.exec_driver_sql("RESET ROLE")
            await connection.commit()
        except BaseException:
            if not connection.closed and not connection.invalidated:
                await connection.invalidate()
            raise

    return heads


def build_alembic_upgrade_callback(
    revision: str = "head",
) -> Callable[[Connection], None]:
    """Build an Alembic upgrade callback using a caller-owned connection."""
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("Alembic revision must not be empty.")

    def upgrade(connection: Connection) -> None:
        from alembic import command
        from alembic.config import Config

        if connection.closed or connection.invalidated:
            raise RuntimeError("Alembic connection is unavailable.")

        project_root = Path(__file__).resolve().parents[3]
        config_path = project_root / "alembic.ini"

        if not config_path.is_file():
            raise FileNotFoundError("Alembic configuration was not found.")

        alembic_config = Config(str(config_path))
        alembic_config.attributes["connection"] = connection

        command.upgrade(alembic_config, revision)

    return upgrade
