"""Asynchronous SQLAlchemy engine and session management."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database_engine(
    database_url: str,
    **engine_options: Any,
) -> AsyncEngine:
    """Create an asynchronous SQLAlchemy engine."""
    engine_options.setdefault("pool_pre_ping", True)
    return create_async_engine(database_url, **engine_options)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a reusable asynchronous session factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session and close it when the request is complete."""
    async with session_factory() as session:
        yield session
