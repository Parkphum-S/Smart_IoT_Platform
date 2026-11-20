"""Coordinate authorized migration execution on one database connection."""

import asyncio
from dataclasses import dataclass
import re
from typing import Callable
from uuid import UUID

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.core.config import settings
from app.infrastructure.database.migration_runner import (
    build_alembic_upgrade_callback,
    read_alembic_current_heads,
    run_migrations_with_connection,
)

from .authorization_audit_repository import AuthorizationAuditRepository
from .authorization_evidence_repository import AuthorizationEvidenceRepository
from .authorization_errors import (
    AuthorizationExecutionError,
    AuthorizationLockError,
)
from .authorization_lock import AuthorizationLockManager, MigrationLock
from .authorization_repository import AuthorizationStateRepository
from .authorization_state import AuthorizationState


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Committed migration execution result."""

    authorization_id: UUID
    state: AuthorizationState
    fencing_token: int
    target_identity: str


class AuthorizationExecutionService:
    """Execute an authorized migration using one caller-owned connection."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        database_role: str | None = None,
    ) -> None:
        role = (
            database_role
            if database_role is not None
            else settings.migration_database_role
        )

        if not isinstance(role, str) or not re.fullmatch(
            r"[a-z_][a-z0-9_]{0,62}", role
        ):
            raise ValueError("Migration database role is invalid.")

        self._engine = engine
        self._database_role = role

    async def _transition(
        self,
        connection: AsyncConnection,
        authorization_id: UUID,
        target_state: AuthorizationState,
        *,
        claimant_id: str,
        fencing_token: int,
        outcome_details: dict | None = None,
    ) -> ExecutionReceipt:
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="control_fully",
        ) as session:
            async with session.begin():
                repository = AuthorizationStateRepository(session)
                audit = AuthorizationAuditRepository()
                evidence = AuthorizationEvidenceRepository()

                execution_sequence = None

                # Allocate while the authorization is still CLAIMED.
                # The target and authorization locks remain held by this
                # transaction through the state transition and evidence insert.
                if target_state in {
                    AuthorizationState.EXECUTING,
                    AuthorizationState.SUCCEEDED,
                    AuthorizationState.UNKNOWN,
                }:
                    # Allocate before transition releases target ownership.
                    execution_sequence = (
                        await evidence.allocate_next_sequence(
                            session,
                            authorization_id=authorization_id,
                            claimant_id=claimant_id,
                            fencing_token=fencing_token,
                        )
                    )

                state = await repository.transition(
                    authorization_id,
                    target_state,
                    claimant_id=claimant_id,
                    expected_fencing_token=fencing_token,
                    outcome_details=outcome_details,
                )

                actions = {
                    AuthorizationState.EXECUTING:
                        "authorization.execution_started",
                    AuthorizationState.SUCCEEDED:
                        "authorization.succeeded",
                    AuthorizationState.FAILED:
                        "authorization.failed",
                    AuthorizationState.UNKNOWN:
                        "authorization.unknown",
                }

                if execution_sequence is not None:
                    evidence_types = {
                        AuthorizationState.EXECUTING:
                            "EXECUTION_STARTED",
                        AuthorizationState.SUCCEEDED:
                            "EXECUTION_COMMITTED",
                        AuthorizationState.UNKNOWN:
                            "EXECUTION_UNCERTAIN",
                    }
                    transitions = {
                        AuthorizationState.EXECUTING:
                            "CLAIMED->EXECUTING",
                        AuthorizationState.SUCCEEDED:
                            "EXECUTING->SUCCEEDED",
                        AuthorizationState.UNKNOWN:
                            "EXECUTING->UNKNOWN",
                    }

                    await evidence.record(
                        session,
                        authorization_id=authorization_id,
                        target_identity=state.target_identity,
                        claimant_id=claimant_id,
                        fencing_token=fencing_token,
                        execution_sequence=execution_sequence,
                        evidence_type=evidence_types[target_state],
                        baseline_revision=state.baseline_revision,
                        expected_revision=state.expected_revision,
                        observed_revision=(
                            state.expected_revision
                            if target_state == AuthorizationState.SUCCEEDED
                            else (
                                state.baseline_revision
                                if target_state == AuthorizationState.EXECUTING
                                else None
                            )
                        ),
                        details={
                            "status": target_state.value,
                            "transition": transitions[target_state],
                        },
                    )

                await audit.record(
                    session,
                    authorization_id=authorization_id,
                    action=actions[target_state],
                    details={
                        "target_identity": state.target_identity,
                        "claimant_id": claimant_id,
                        "fencing_token": fencing_token,
                        "status": target_state.value,
                        "outcome_details": outcome_details or {},
                    },
                )

                receipt = ExecutionReceipt(
                    authorization_id=authorization_id,
                    state=target_state,
                    fencing_token=fencing_token,
                    target_identity=state.target_identity,
                )

        return receipt

    async def _record_execution_evidence(
        self,
        connection: AsyncConnection,
        authorization_id: UUID,
        *,
        claimant_id: str,
        fencing_token: int,
        evidence_type: str,
        observed_revision: str | None = None,
    ) -> None:
        """Persist one execution evidence record in its own transaction."""

        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="control_fully",
        ) as session:
            async with session.begin():
                repository = AuthorizationStateRepository(session)
                evidence = AuthorizationEvidenceRepository()

                sequence = await evidence.allocate_next_sequence(
                    session,
                    authorization_id=authorization_id,
                    claimant_id=claimant_id,
                    fencing_token=fencing_token,
                )

                state = await repository.get_by_id(authorization_id)

                if (
                    state.status != AuthorizationState.EXECUTING.value
                    or state.claimant_id != claimant_id
                    or state.fencing_token != fencing_token
                ):
                    raise AuthorizationExecutionError(
                        "Execution evidence ownership validation failed."
                    )

                await evidence.record(
                    session,
                    authorization_id=authorization_id,
                    target_identity=state.target_identity,
                    claimant_id=claimant_id,
                    fencing_token=fencing_token,
                    execution_sequence=sequence,
                    evidence_type=evidence_type,
                    baseline_revision=state.baseline_revision,
                    expected_revision=state.expected_revision,
                    observed_revision=observed_revision,
                    details={
                        "status": state.status,
                        "evidence_type": evidence_type,
                    },
                )

    async def execute(
        self,
        authorization_id: UUID,
        *,
        claimant_id: str,
        migration_callback: Callable[[Connection], None],
    ) -> ExecutionReceipt:
        """Claim, lock, execute, and persist the migration outcome."""

        if not claimant_id or not claimant_id.strip():
            raise ValueError("Claimant identity must not be empty.")

        if not callable(migration_callback):
            raise TypeError("Migration callback must be callable.")

        lock_manager = None
        lock: MigrationLock | None = None
        executing = False
        fencing_token: int | None = None
        target_identity: str | None = None
        baseline_revision: str | None = None
        expected_revision: str | None = None

        async with self._engine.connect() as connection:
            try:
                # Read authorization before acquiring the target lock.
                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="control_fully",
                ) as session:
                    async with session.begin():
                        repository = AuthorizationStateRepository(session)
                        state = await repository.get_by_id(authorization_id)

                        if state.status != AuthorizationState.ISSUED.value:
                            raise AuthorizationExecutionError(
                                "Authorization is not in ISSUED state."
                            )

                        target_identity = state.target_identity
                        baseline_revision = state.baseline_revision
                        expected_revision = state.expected_revision

                # Acquire the target lock before claiming authorization.
                lock_manager = AuthorizationLockManager(connection)
                lock = await lock_manager.acquire(target_identity)

                if not lock.acquired:
                    raise AuthorizationLockError(
                        "Migration target is already locked."
                    )

                # Verify the authorized baseline while holding the target lock.
                current_heads = await read_alembic_current_heads(
                    connection,
                    self._database_role,
                )

                if (
                    len(current_heads) != 1
                    or current_heads[0] != baseline_revision
                ):
                    raise AuthorizationExecutionError(
                        "Target database revision does not match "
                        "the authorized baseline."
                    )

                # T1: atomic claim and audit.
                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="control_fully",
                ) as session:
                    async with session.begin():
                        repository = AuthorizationStateRepository(session)
                        audit = AuthorizationAuditRepository()

                        claim = await repository.claim(
                            authorization_id,
                            claimant_id=claimant_id,
                        )

                        fencing_token = claim.fencing_token

                        await audit.record(
                            session,
                            authorization_id=authorization_id,
                            action="authorization.claimed",
                            details={
                                "target_identity": target_identity,
                                "claimant_id": claimant_id,
                                "fencing_token": fencing_token,
                                "status": AuthorizationState.CLAIMED.value,
                            },
                        )

                # T2: persist EXECUTING before invoking migration.
                await self._transition(
                    connection,
                    authorization_id,
                    AuthorizationState.EXECUTING,
                    claimant_id=claimant_id,
                    fencing_token=fencing_token,
                )
                executing = True

                # Migration uses the same PostgreSQL connection and lock.
                await run_migrations_with_connection(
                    connection,
                    self._database_role,
                    migration_callback,
                )

                # Persist callback completion before revision inspection.
                await self._record_execution_evidence(
                    connection,
                    authorization_id,
                    claimant_id=claimant_id,
                    fencing_token=fencing_token,
                    evidence_type="MIGRATION_RETURNED",
                )

                # Verify the authorized expected revision before success.
                final_heads = await read_alembic_current_heads(
                    connection,
                    self._database_role,
                )

                if (
                    len(final_heads) != 1
                    or final_heads[0] != expected_revision
                ):
                    raise AuthorizationExecutionError(
                        "Target database revision does not match "
                        "the authorized expected revision."
                    )

                # Persist proof of the observed expected revision.
                await self._record_execution_evidence(
                    connection,
                    authorization_id,
                    claimant_id=claimant_id,
                    fencing_token=fencing_token,
                    evidence_type="REVISION_VERIFIED",
                    observed_revision=final_heads[0],
                )

                # T4: persist success and audit atomically.
                receipt = await self._transition(
                    connection,
                    authorization_id,
                    AuthorizationState.SUCCEEDED,
                    claimant_id=claimant_id,
                    fencing_token=fencing_token,
                    outcome_details={"execution": "completed"},
                )
                executing = False
                return receipt

            except asyncio.CancelledError:
                if executing and fencing_token is not None:
                    # Cancellation during execution has an uncertain outcome.
                    # Persist UNKNOWN before releasing the advisory lock.
                    try:
                        await self._transition(
                            connection,
                            authorization_id,
                            AuthorizationState.UNKNOWN,
                            claimant_id=claimant_id,
                            fencing_token=fencing_token,
                            outcome_details={
                                "execution": "cancelled_requires_reconciliation",
                                "error_type": "CancelledError",
                            },
                        )
                    except Exception:
                        # Preserve target ownership and allow recovery
                        # to inspect the persisted execution state.
                        pass

                # Cancellation must always propagate to the caller.
                raise

            except Exception as exc:
                if executing and fencing_token is not None:
                    # An execution exception is conservatively UNKNOWN.
                    # Never infer migration failure from an exception alone.
                    try:
                        await self._transition(
                            connection,
                            authorization_id,
                            AuthorizationState.UNKNOWN,
                            claimant_id=claimant_id,
                            fencing_token=fencing_token,
                            outcome_details={
                                "execution": "requires_reconciliation",
                                "error_type": type(exc).__name__,
                            },
                        )
                    except Exception:
                        # Preserve the original failure. Recovery must inspect
                        # persisted state and migration history separately.
                        pass

                if isinstance(exc, AuthorizationExecutionError):
                    raise

                raise AuthorizationExecutionError(
                    "Authorized migration execution could not be confirmed."
                ) from exc

            finally:
                if (
                    lock_manager is not None
                    and lock is not None
                    and lock.acquired
                ):
                    try:
                        if (
                            not connection.closed
                            and not connection.invalidated
                        ):
                            await lock_manager.release(lock)

                    except asyncio.CancelledError:
                        # Cancellation must propagate, but the connection
                        # must not return to the pool with uncertain lock state.
                        if (
                            not connection.closed
                            and not connection.invalidated
                        ):
                            try:
                                await connection.invalidate()
                            except Exception:
                                pass
                        raise

                    except Exception:
                        # A failed unlock must never return a possibly
                        # lock-holding PostgreSQL session to the pool.
                        if (
                            not connection.closed
                            and not connection.invalidated
                        ):
                            try:
                                await connection.invalidate()
                            except Exception:
                                pass


    async def execute_alembic(
        self,
        authorization_id: UUID,
        *,
        claimant_id: str,
    ) -> ExecutionReceipt:
        """Execute the revision explicitly bound to the authorization."""

        async with self._engine.connect() as connection:
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="control_fully",
            ) as session:
                async with session.begin():
                    repository = AuthorizationStateRepository(session)
                    state = await repository.get_by_id(authorization_id)

                    if state.status != AuthorizationState.ISSUED.value:
                        raise AuthorizationExecutionError(
                            "Authorization is not in ISSUED state."
                        )

                    expected_revision = state.expected_revision

        if not expected_revision or not expected_revision.strip():
            raise AuthorizationExecutionError(
                "Authorization has no valid expected revision."
            )

        migration_callback = build_alembic_upgrade_callback(
            expected_revision
        )

        return await self.execute(
            authorization_id,
            claimant_id=claimant_id,
            migration_callback=migration_callback,
        )
