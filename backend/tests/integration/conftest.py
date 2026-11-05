"""Integration test fixtures and fail-closed database safety guard."""

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.infrastructure.database.session import create_database_engine


EXPECTED_DATABASE = "smart_iot_integration_test"
EXPECTED_APP_ROLE = "smart_iot_test_app"
EXPECTED_MIGRATOR_ROLE = "smart_iot_test_migrator"
EXPECTED_OWNER_ROLE = "smart_iot_test_owner"


@pytest.fixture(scope="session", autouse=True)
def integration_database_guard():
    """Reject integration tests unless every database target is approved."""
    settings = get_settings()
    errors = []

    if settings.app_env != "testing":
        errors.append("APP_ENV must be testing")

    app_url = make_url(str(settings.database_url))

    if app_url.database != EXPECTED_DATABASE:
        errors.append("DATABASE_URL must target the integration test database")

    if app_url.username != EXPECTED_APP_ROLE:
        errors.append("DATABASE_URL must use the integration application role")

    migration_url = settings.migration_database_url

    if migration_url is None:
        errors.append("MIGRATION_DATABASE_URL must be configured")
    else:
        parsed_migration_url = make_url(str(migration_url))

        if parsed_migration_url.database != EXPECTED_DATABASE:
            errors.append(
                "MIGRATION_DATABASE_URL must target the integration test database"
            )

        if parsed_migration_url.username != EXPECTED_MIGRATOR_ROLE:
            errors.append(
                "MIGRATION_DATABASE_URL must use the integration migrator role"
            )

    if settings.migration_database_role != EXPECTED_OWNER_ROLE:
        errors.append(
            "MIGRATION_DATABASE_ROLE must be the integration owner role"
        )

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise pytest.UsageError(
            "Database Guard blocked integration tests:\n" + details
        )


@pytest.fixture
async def db_engine():
    """Create an engine for the approved integration database."""
    settings = get_settings()
    engine = create_database_engine(
        str(settings.database_url),
        pool_pre_ping=True,
    )

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Provide a session isolated by an outer rollback-only transaction."""
    async with db_engine.connect() as connection:
        outer_transaction = await connection.begin()

        try:
            session_factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            async with session_factory() as session:
                yield session
        finally:
            if outer_transaction.is_active:
                await outer_transaction.rollback()
