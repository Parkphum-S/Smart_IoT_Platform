"""Fail-closed recovery inspection for unknown migrations."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from .authorization_audit_repository import AuthorizationAuditRepository
from .authorization_evidence_repository import AuthorizationEvidenceRepository
from .authorization_errors import (
    AuthorizationIntegrityError,
    AuthorizationLockError,
    AuthorizationNotFoundError,
    AuthorizationStateConflictError,
)
from .authorization_lock import AuthorizationLockManager, MigrationLock
from .authorization_models import (
    MigrationAuthorizationState,
    MigrationTargetState,
)
from .authorization_recovery_decision import (
    RecoveryDecision,
    RecoveryDecisionReason,
    RecoveryDecisionResult,
    evaluate_recovery_evidence,
)
from .authorization_recovery_evidence import (
    RecoveryEvidence,
    RecoveryEvidenceProvider,
)
from .authorization_state import AuthorizationState


@dataclass(frozen=True, slots=True)
class RecoveryReceipt:
    """Immutable receipt for a non-terminal recovery inspection."""

    authorization_id: UUID
    target_identity: str
    claimant_id: str
    fencing_token: int
    decision: RecoveryDecision
    reason: RecoveryDecisionReason
    evidence: RecoveryEvidence


class AuthorizationRecoveryService:
    """Inspect UNKNOWN authorizations without releasing target ownership."""

    def __init__(
        self,
        engine: AsyncEngine,
        evidence_provider: RecoveryEvidenceProvider,
    ) -> None:
        if not isinstance(evidence_provider, RecoveryEvidenceProvider):
            raise TypeError("A recovery evidence provider is required.")

        self._engine = engine
        self._evidence_provider = evidence_provider
        self._audit = AuthorizationAuditRepository()

    async def reconcile(
        self,
        authorization_id: UUID,
        *,
        claimant_id: str,
        fencing_token: int,
    ) -> RecoveryReceipt:
        """Inspect revision evidence and retain UNKNOWN ownership."""

        if not isinstance(authorization_id, UUID):
            raise TypeError("Authorization ID must be a UUID.")

        if not isinstance(claimant_id, str) or not claimant_id.strip():
            raise ValueError("Claimant identity is required.")

        if (
            not isinstance(fencing_token, int)
            or isinstance(fencing_token, bool)
            or fencing_token <= 0
        ):
            raise ValueError("Fencing token is invalid.")

        async with self._engine.connect() as connection:
            lock_manager = AuthorizationLockManager(connection)
            lock: MigrationLock | None = None

            try:
                identity_result = await connection.execute(
                    text(
                        "SELECT target_identity "
                        "FROM migration_authorization_states "
                        "WHERE id = :authorization_id"
                    ),
                    {"authorization_id": authorization_id},
                )
                target_identity = identity_result.scalar_one_or_none()

                await connection.commit()

                if target_identity is None:
                    raise AuthorizationNotFoundError(
                        "Authorization state was not found."
                    )

                lock = await lock_manager.acquire(target_identity)

                if not lock.acquired:
                    await connection.commit()
                    raise AuthorizationLockError(
                        "Migration target is currently locked."
                    )

                baseline_revision = await self._get_revision_value(
                    connection,
                    authorization_id,
                    "baseline_revision",
                )
                expected_revision = await self._get_revision_value(
                    connection,
                    authorization_id,
                    "expected_revision",
                )

                evidence = await self._evidence_provider.collect(
                    connection,
                    baseline_revision=baseline_revision,
                    expected_revision=expected_revision,
                )

                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="control_fully",
                ) as session:
                    async with session.begin():
                        target_result = await session.execute(
                            select(MigrationTargetState)
                            .where(
                                MigrationTargetState.target_identity
                                == target_identity
                            )
                            .with_for_update()
                        )
                        target = target_result.scalar_one_or_none()

                        auth_result = await session.execute(
                            select(MigrationAuthorizationState)
                            .where(
                                MigrationAuthorizationState.id
                                == authorization_id
                            )
                            .with_for_update()
                        )
                        state = auth_result.scalar_one_or_none()

                        if target is None or state is None:
                            raise AuthorizationNotFoundError(
                                "Recovery ownership records were not found."
                            )

                        if state.target_identity != target_identity:
                            raise AuthorizationIntegrityError(
                                "Authorization target identity changed."
                            )

                        if state.status != AuthorizationState.UNKNOWN.value:
                            raise AuthorizationStateConflictError(
                                "Only UNKNOWN authorizations can be recovered."
                            )

                        if (
                            state.claimant_id != claimant_id
                            or state.fencing_token != fencing_token
                            or target.active_authorization_id
                            != authorization_id
                            or target.active_claimant_id != claimant_id
                            or target.fencing_token != fencing_token
                        ):
                            raise AuthorizationStateConflictError(
                                "Recovery claimant or target ownership "
                                "does not match."
                            )

                        if (
                            evidence.baseline_revision
                            != state.baseline_revision
                            or evidence.expected_revision
                            != state.expected_revision
                        ):
                            raise AuthorizationIntegrityError(
                                "Recovery evidence does not match "
                                "the authorization revision contract."
                            )

                        evidence_repository = (
                            AuthorizationEvidenceRepository()
                        )
                        execution_records = (
                            await evidence_repository.list_by_authorization(
                                session,
                                authorization_id,
                            )
                        )

                        execution_evidence_summary = (
                            self._validate_execution_evidence(
                                execution_records,
                                authorization_id=authorization_id,
                                target_identity=target_identity,
                                claimant_id=claimant_id,
                                fencing_token=fencing_token,
                                baseline_revision=state.baseline_revision,
                                expected_revision=state.expected_revision,
                            )
                        )

                        result: RecoveryDecisionResult = (
                            evaluate_recovery_evidence(evidence)
                        )

                        await self._audit.record(
                            session,
                            authorization_id=authorization_id,
                            action="authorization.recovery_unresolved",
                            details={
                                "target_identity": target_identity,
                                "claimant_id": claimant_id,
                                "fencing_token": fencing_token,
                                "decision": result.decision.value,
                                "reason": result.reason.value,
                                "evidence_position":
                                    result.evidence_position.value,
                                "observed_heads": list(
                                    evidence.observed_heads
                                ),
                                "baseline_revision":
                                    evidence.baseline_revision,
                                "expected_revision":
                                    evidence.expected_revision,
                                "revision_path": list(
                                    evidence.revision_path
                                ),
                                "direction": evidence.direction,
                                "execution_evidence":
                                    execution_evidence_summary,
                            },
                        )

                        receipt = RecoveryReceipt(
                            authorization_id=authorization_id,
                            target_identity=target_identity,
                            claimant_id=claimant_id,
                            fencing_token=fencing_token,
                            decision=result.decision,
                            reason=result.reason,
                            evidence=evidence,
                        )

                return receipt

            finally:
                try:
                    # Clear failed or unfinished transactions first.
                    # Session-level advisory locks survive transaction rollback.
                    if connection.in_transaction():
                        await connection.rollback()

                    if lock is not None and lock.acquired:
                        await lock_manager.release(lock)
                        await connection.commit()

                except BaseException:
                    # Never return a connection with uncertain lock ownership
                    # to the connection pool.
                    try:
                        await connection.invalidate()
                    except BaseException:
                        pass
                    raise

    @staticmethod
    def _validate_execution_evidence(
        records,
        *,
        authorization_id: UUID,
        target_identity: str,
        claimant_id: str,
        fencing_token: int,
        baseline_revision: str,
        expected_revision: str,
    ) -> dict:
        """Validate durable execution evidence without changing lifecycle."""

        if not records:
            return {
                "record_count": 0,
                "sequence_valid": False,
                "binding_valid": False,
                "event_order_valid": False,
                "complete": False,
                "evidence_types": [],
                "terminal_type": None,
            }

        allowed_types = {
            "EXECUTION_STARTED",
            "MIGRATION_RETURNED",
            "REVISION_VERIFIED",
            "EXECUTION_COMMITTED",
            "EXECUTION_UNCERTAIN",
        }

        observed_revisions = {
            "EXECUTION_STARTED": baseline_revision,
            "MIGRATION_RETURNED": None,
            "REVISION_VERIFIED": expected_revision,
            "EXECUTION_COMMITTED": expected_revision,
            "EXECUTION_UNCERTAIN": None,
        }

        evidence_types = []
        positions = {}

        for expected_sequence, record in enumerate(records, start=1):
            if record.execution_sequence != expected_sequence:
                raise AuthorizationIntegrityError(
                    "Execution evidence sequence contains a gap."
                )

            if (
                record.authorization_id != authorization_id
                or record.target_identity != target_identity
                or record.claimant_id != claimant_id
                or record.fencing_token != fencing_token
                or record.baseline_revision != baseline_revision
                or record.expected_revision != expected_revision
            ):
                raise AuthorizationIntegrityError(
                    "Execution evidence ownership binding mismatch."
                )

            evidence_type = record.evidence_type

            if evidence_type not in allowed_types:
                raise AuthorizationIntegrityError(
                    "Execution evidence type is not recognized."
                )

            if evidence_type in positions:
                raise AuthorizationIntegrityError(
                    "Duplicate execution evidence event."
                )

            if record.observed_revision != observed_revisions[evidence_type]:
                raise AuthorizationIntegrityError(
                    "Execution evidence revision binding mismatch."
                )

            positions[evidence_type] = expected_sequence - 1
            evidence_types.append(evidence_type)

        if evidence_types[0] != "EXECUTION_STARTED":
            raise AuthorizationIntegrityError(
                "Execution evidence must begin with EXECUTION_STARTED."
            )

        if (
            "MIGRATION_RETURNED" in positions
            and positions["MIGRATION_RETURNED"] != 1
        ):
            raise AuthorizationIntegrityError(
                "MIGRATION_RETURNED event ordering is invalid."
            )

        if (
            "REVISION_VERIFIED" in positions
            and (
                "MIGRATION_RETURNED" not in positions
                or positions["REVISION_VERIFIED"] != 2
            )
        ):
            raise AuthorizationIntegrityError(
                "REVISION_VERIFIED event ordering is invalid."
            )

        terminal_type = evidence_types[-1]

        if "EXECUTION_COMMITTED" in positions:
            if (
                "REVISION_VERIFIED" not in positions
                or positions["EXECUTION_COMMITTED"] != len(records) - 1
                or "EXECUTION_UNCERTAIN" in positions
            ):
                raise AuthorizationIntegrityError(
                    "EXECUTION_COMMITTED event ordering is invalid."
                )

            raise AuthorizationIntegrityError(
                "UNKNOWN authorization conflicts with committed evidence."
            )

        if (
            "EXECUTION_UNCERTAIN" in positions
            and positions["EXECUTION_UNCERTAIN"] != len(records) - 1
        ):
            raise AuthorizationIntegrityError(
                "EXECUTION_UNCERTAIN must be the final event."
            )

        return {
            "record_count": len(records),
            "sequence_valid": True,
            "binding_valid": True,
            "event_order_valid": True,
            "complete": terminal_type == "EXECUTION_UNCERTAIN",
            "evidence_types": evidence_types,
            "terminal_type": (
                terminal_type
                if terminal_type in {
                    "EXECUTION_UNCERTAIN",
                    "EXECUTION_COMMITTED",
                }
                else None
            ),
        }

    @staticmethod
    async def _get_revision_value(
        connection: AsyncConnection,
        authorization_id: UUID,
        field: str,
    ) -> str:
        """Read one fixed authorization revision field."""

        columns = {
            "baseline_revision",
            "expected_revision",
        }

        if field not in columns:
            raise ValueError("Unsupported revision field.")

        result = await connection.execute(
            text(
                f"SELECT {field} "
                "FROM migration_authorization_states "
                "WHERE id = :authorization_id"
            ),
            {"authorization_id": authorization_id},
        )

        value = result.scalar_one_or_none()

        if not isinstance(value, str) or not value:
            raise AuthorizationIntegrityError(
                "Authorization revision contract is incomplete."
            )

        return value
