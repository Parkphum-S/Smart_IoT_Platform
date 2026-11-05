"""FastAPI application factory and application lifecycle."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.workspaces import router as workspaces_router
from app.api.memberships import router as memberships_router

from app.core.config import get_settings
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application resources during startup and shutdown."""
    settings = get_settings()

    engine = create_database_engine(
        str(settings.database_url),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )

    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)

    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    application.include_router(health_router)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(workspaces_router, prefix=settings.api_v1_prefix)
    application.include_router(memberships_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
