"""Append-only repository for durable execution evidence."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .authorization_errors import (
    AuthorizationIntegrityError,
    AuthorizationNotFoundError,
    AuthorizationPersistenceError,
    AuthorizationStateConflictError,
)
from .authorization_evidence_models import (
    EVIDENCE_TYPES,
    MigrationExecutionEvidence,
)
from .authorization_models import (
    MigrationAuthorizationState,
    MigrationTargetState,
)


class AuthorizationEvidenceRepository:
    """Persist and retrieve immutable execution evidence.

    The caller owns the AsyncSession and surrounding transaction.
    This repository never commits, rolls back, or creates connections.
    """

    async def record(
        self,
        session: AsyncSession,
        *,
        authorization_id: UUID,
        target_identity: str,
        claimant_id: str,
        fencing_token: int,
        execution_sequence: int,
        evidence_type: str,
        baseline_revision: str,
        expected_revision: str,
        observed_revision: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> MigrationExecutionEvidence:
        """Append one evidence record to the caller-owned transaction."""

        if not isinstance(authorization_id, UUID):
            raise AuthorizationIntegrityError(
                "Evidence authorization ID must be a UUID."
            )

        if not isinstance(target_identity, str) or not target_identity.strip():
            raise AuthorizationIntegrityError(
                "Evidence target identity must not be empty."
            )

        if not isinstance(claimant_id, str) or not claimant_id.strip():
            raise AuthorizationIntegrityError(
                "Evidence claimant identity must not be empty."
            )

        if (
            not isinstance(fencing_token, int)
            or isinstance(fencing_token, bool)
            or fencing_token <= 0
        ):
            raise AuthorizationIntegrityError(
                "Evidence fencing token must be positive."
            )

        if (
            not isinstance(execution_sequence, int)
            or isinstance(execution_sequence, bool)
            or execution_sequence <= 0
        ):
            raise AuthorizationIntegrityError(
                "Evidence sequence must be positive."
            )

        if evidence_type not in EVIDENCE_TYPES:
            raise AuthorizationIntegrityError(
                "Evidence type is not allowed."
            )

        if not isinstance(baseline_revision, str) or not baseline_revision:
            raise AuthorizationIntegrityError(
                "Evidence baseline revision must not be empty."
            )

        if not isinstance(expected_revision, str) or not expected_revision:
            raise AuthorizationIntegrityError(
                "Evidence expected revision must not be empty."
            )

        if observed_revision is not None and not isinstance(
            observed_revision, str
        ):
            raise AuthorizationIntegrityError(
                "Observed revision must be a string or None."
            )

        if details is not None and not isinstance(details, dict):
            raise AuthorizationIntegrityError(
                "Evidence details must be a dictionary."
            )

        evidence = MigrationExecutionEvidence(
            authorization_id=authorization_id,
            target_identity=target_identity,
            claimant_id=claimant_id,
            fencing_token=fencing_token,
            execution_sequence=execution_sequence,
            evidence_type=evidence_type,
            baseline_revision=baseline_revision,
            expected_revision=expected_revision,
            observed_revision=observed_revision,
            details=details if details is not None else {},
        )

        try:
            session.add(evidence)
            await session.flush()
            return evidence
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not persist execution evidence."
            ) from exc


    async def allocate_next_sequence(
        self,
        session: AsyncSession,
        *,
        authorization_id: UUID,
        claimant_id: str,
        fencing_token: int,
    ) -> int:
        """Allocate the next sequence under target ownership locks."""

        if not session.in_transaction():
            raise AuthorizationIntegrityError(
                "An active caller-owned transaction is required."
            )

        if not isinstance(authorization_id, UUID):
            raise AuthorizationIntegrityError("Invalid authorization ID.")

        if not isinstance(claimant_id, str) or not claimant_id.strip():
            raise AuthorizationIntegrityError("Invalid claimant ID.")

        if (
            not isinstance(fencing_token, int)
            or isinstance(fencing_token, bool)
            or fencing_token <= 0
        ):
            raise AuthorizationIntegrityError("Invalid fencing token.")

        try:
            identity_result = await session.execute(
                select(MigrationAuthorizationState.target_identity).where(
                    MigrationAuthorizationState.id == authorization_id
                )
            )
            target_identity = identity_result.scalar_one_or_none()

            if target_identity is None:
                raise AuthorizationNotFoundError(
                    "Authorization state was not found."
                )

            target_result = await session.execute(
                select(MigrationTargetState)
                .where(
                    MigrationTargetState.target_identity == target_identity
                )
                .with_for_update()
            )
            target = target_result.scalar_one_or_none()

            if target is None:
                raise AuthorizationStateConflictError(
                    "Target ownership record was not found."
                )

            state_result = await session.execute(
                select(MigrationAuthorizationState)
                .where(
                    MigrationAuthorizationState.id == authorization_id
                )
                .with_for_update()
            )
            state = state_result.scalar_one_or_none()

            if state is None:
                raise AuthorizationNotFoundError(
                    "Authorization state was not found."
                )

            if (
                state.target_identity != target_identity
                or state.status not in {"CLAIMED", "EXECUTING", "UNKNOWN"}
                or state.claimant_id != claimant_id
                or state.fencing_token != fencing_token
                or target.active_authorization_id != authorization_id
                or target.active_claimant_id != claimant_id
                or target.fencing_token != fencing_token
            ):
                raise AuthorizationStateConflictError(
                    "Authorization ownership or fencing mismatch."
                )

            result = await session.execute(
                select(MigrationExecutionEvidence.execution_sequence)
                .where(
                    MigrationExecutionEvidence.authorization_id
                    == authorization_id
                )
                .order_by(
                    MigrationExecutionEvidence.execution_sequence.asc()
                )
            )
            sequences = result.scalars().all()

            if any(
                actual != expected
                for expected, actual in enumerate(sequences, start=1)
            ):
                raise AuthorizationIntegrityError(
                    "Evidence sequence contains a gap."
                )

            return len(sequences) + 1

        except (
            AuthorizationIntegrityError,
            AuthorizationNotFoundError,
            AuthorizationStateConflictError,
        ):
            raise
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not allocate evidence sequence."
            ) from exc

    async def get_by_id(
        self,
        session: AsyncSession,
        evidence_id: UUID,
    ) -> MigrationExecutionEvidence | None:
        """Retrieve one evidence record by its UUID."""

        try:
            result = await session.execute(
                select(MigrationExecutionEvidence).where(
                    MigrationExecutionEvidence.id == evidence_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not retrieve execution evidence."
            ) from exc

    async def list_by_authorization(
        self,
        session: AsyncSession,
        authorization_id: UUID,
    ) -> list[MigrationExecutionEvidence]:
        """Retrieve evidence in execution sequence order."""

        try:
            result = await session.execute(
                select(MigrationExecutionEvidence)
                .where(
                    MigrationExecutionEvidence.authorization_id
                    == authorization_id
                )
                .order_by(
                    MigrationExecutionEvidence.execution_sequence.asc()
                )
            )
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not list authorization execution evidence."
            ) from exc

    async def get_latest(
        self,
        session: AsyncSession,
        authorization_id: UUID,
    ) -> MigrationExecutionEvidence | None:
        """Retrieve the latest evidence for one authorization."""

        try:
            result = await session.execute(
                select(MigrationExecutionEvidence)
                .where(
                    MigrationExecutionEvidence.authorization_id
                    == authorization_id
                )
                .order_by(
                    MigrationExecutionEvidence.execution_sequence.desc()
                )
                .limit(1)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not retrieve latest execution evidence."
            ) from exc

    async def verify_sequence(
        self,
        session: AsyncSession,
        authorization_id: UUID,
    ) -> bool:
        """Verify that persisted evidence sequences are contiguous from one."""

        records = await self.list_by_authorization(
            session,
            authorization_id,
        )

        return all(
            record.execution_sequence == expected
            for expected, record in enumerate(records, start=1)
        )
