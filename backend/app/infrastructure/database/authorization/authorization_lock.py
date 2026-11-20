"""PostgreSQL advisory lock manager for migration targets."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from .authorization_errors import AuthorizationLockError


_LOCK_NAMESPACE = b"smart-iot:migration-target:v1:"


@dataclass(frozen=True, slots=True)
class MigrationLock:
    """Immutable receipt describing a target advisory lock."""

    target_identity: str
    lock_key: int
    acquired: bool


class AuthorizationLockManager:
    """Manage session-level advisory locks on a caller-owned connection."""

    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._active_lock: MigrationLock | None = None

    @staticmethod
    def build_lock_key(target_identity: str) -> int:
        """Build a deterministic signed PostgreSQL BIGINT lock key."""

        if not isinstance(target_identity, str) or not target_identity.strip():
            raise ValueError("Target identity must be a non-empty string.")

        digest = hashlib.sha256(
            _LOCK_NAMESPACE + target_identity.encode("utf-8")
        ).digest()

        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    def verify_connection(self) -> None:
        """Reject a closed or invalidated connection."""

        if self._connection.closed or self._connection.invalidated:
            raise AuthorizationLockError(
                "Migration lock connection is unavailable."
            )

    async def acquire(self, target_identity: str) -> MigrationLock:
        """Acquire a non-blocking session-level advisory lock."""

        self.verify_connection()

        if self._active_lock is not None:
            raise AuthorizationLockError(
                "This lock manager already holds an advisory lock."
            )

        lock_key = self.build_lock_key(target_identity)

        try:
            result = await self._connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": lock_key},
            )
            acquired = bool(result.scalar_one())

        except SQLAlchemyError as exc:
            raise AuthorizationLockError(
                "PostgreSQL advisory lock acquisition failed."
            ) from exc

        lock = MigrationLock(
            target_identity=target_identity,
            lock_key=lock_key,
            acquired=acquired,
        )

        if acquired:
            self._active_lock = lock

        return lock

    async def release(self, lock: MigrationLock) -> None:
        """Release a lock using the same caller-owned connection."""

        self.verify_connection()

        if (
            not isinstance(lock, MigrationLock)
            or not lock.acquired
            or self._active_lock is not lock
        ):
            raise AuthorizationLockError(
                "Lock ownership does not match this lock manager."
            )

        try:
            result = await self._connection.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": lock.lock_key},
            )
            released = bool(result.scalar_one())

        except SQLAlchemyError as exc:
            raise AuthorizationLockError(
                "PostgreSQL advisory lock release failed."
            ) from exc

        if not released:
            self._active_lock = None
            raise AuthorizationLockError(
                "PostgreSQL reported that the advisory lock was not held."
            )

        self._active_lock = None
