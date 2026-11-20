"""Repository for migration authorization state persistence."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .authorization_state import (
    AuthorizationState,
    validate_transition,
)
from .authorization_errors import (
    AuthorizationAlreadyClaimedError,
    AuthorizationExpiredError,
    AuthorizationIntegrityError,
    AuthorizationNotFoundError,
    AuthorizationPersistenceError,
    AuthorizationStateConflictError,
)
from .authorization_models import (
    MigrationAuthorizationState,
    MigrationTargetState,
)


@dataclass(frozen=True, slots=True)
class AuthorizationClaim:
    """Result of an atomic target-scoped authorization claim."""

    state: MigrationAuthorizationState
    fencing_token: int


class AuthorizationStateRepository:
    """Persist, retrieve, and atomically claim authorization state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        manifest_digest: str,
        target_identity: str,
        environment: str,
        operation: str,
        policy_version: str,
        baseline_revision: str,
        expected_revision: str,
        issued_at: datetime,
        expires_at: datetime,
        outcome_details: dict[str, Any] | None = None,
    ) -> MigrationAuthorizationState:
        """Create a new ISSUED authorization state."""

        state = MigrationAuthorizationState(
            manifest_digest=manifest_digest,
            target_identity=target_identity,
            environment=environment,
            operation=operation,
            policy_version=policy_version,
            baseline_revision=baseline_revision,
            expected_revision=expected_revision,
            status="ISSUED",
            fencing_token=0,
            issued_at=issued_at,
            expires_at=expires_at,
            outcome_details=(
                outcome_details if outcome_details is not None else {}
            ),
        )

        try:
            self._session.add(state)
            await self._session.flush()
            return state
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not create authorization state."
            ) from exc

    async def get_by_id(
        self,
        authorization_id: UUID,
    ) -> MigrationAuthorizationState:
        """Retrieve authorization state by primary key."""

        try:
            result = await self._session.execute(
                select(MigrationAuthorizationState).where(
                    MigrationAuthorizationState.id == authorization_id
                )
            )
            state = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not retrieve authorization state."
            ) from exc

        if state is None:
            raise AuthorizationNotFoundError(
                "Authorization state was not found."
            )

        return state

    async def get_by_target(
        self,
        target_identity: str,
    ) -> list[MigrationAuthorizationState]:
        """Retrieve authorization states belonging to a target."""

        try:
            result = await self._session.execute(
                select(MigrationAuthorizationState)
                .where(
                    MigrationAuthorizationState.target_identity
                    == target_identity
                )
                .order_by(MigrationAuthorizationState.issued_at.desc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not retrieve target authorization states."
            ) from exc

    async def claim(
        self,
        authorization_id: UUID,
        *,
        claimant_id: str,
    ) -> AuthorizationClaim:
        """Atomically claim an authorization and its migration target.

        The caller owns the surrounding transaction and must commit or
        roll back the complete operation.
        """

        if not claimant_id or not claimant_id.strip():
            raise AuthorizationIntegrityError(
                "Claimant identity must not be empty."
            )

        try:
            # Read the target identity to establish the target lock first.
            identity_result = await self._session.execute(
                select(MigrationAuthorizationState.target_identity).where(
                    MigrationAuthorizationState.id == authorization_id
                )
            )
            target_identity = identity_result.scalar_one_or_none()

            if target_identity is None:
                raise AuthorizationNotFoundError(
                    "Authorization state was not found."
                )

            # Ensure the target row exists. Concurrent inserts are harmless.
            await self._session.execute(
                pg_insert(MigrationTargetState)
                .values(target_identity=target_identity)
                .on_conflict_do_nothing(
                    index_elements=["target_identity"]
                )
            )

            # Serialize all claims targeting this database identity.
            target_result = await self._session.execute(
                select(MigrationTargetState)
                .where(
                    MigrationTargetState.target_identity == target_identity
                )
                .with_for_update()
            )
            target = target_result.scalar_one()

            if target.active_authorization_id is not None:
                raise AuthorizationAlreadyClaimedError(
                    "Migration target already has an active authorization."
                )

            # Lock the authorization row before validating its lifecycle.
            auth_result = await self._session.execute(
                select(MigrationAuthorizationState)
                .where(
                    MigrationAuthorizationState.id == authorization_id
                )
                .with_for_update()
            )
            state = auth_result.scalar_one_or_none()

            if state is None:
                raise AuthorizationNotFoundError(
                    "Authorization state was not found."
                )

            if state.target_identity != target_identity:
                raise AuthorizationIntegrityError(
                    "Authorization target identity changed during claim."
                )

            if state.status != "ISSUED":
                raise AuthorizationAlreadyClaimedError(
                    "Authorization is not in ISSUED state."
                )

            # Use database time, not the application host clock.
            db_now = await self._session.scalar(select(func.clock_timestamp()))

            if db_now is None:
                raise AuthorizationPersistenceError(
                    "Database time could not be determined."
                )

            if state.expires_at <= db_now:
                raise AuthorizationExpiredError(
                    "Authorization capability has expired."
                )

            # Increment the target-scoped fencing token.
            target.fencing_token += 1
            target.active_authorization_id = state.id
            target.active_claimant_id = claimant_id
            target.lease_acquired_at = db_now

            state.status = "CLAIMED"
            state.claimant_id = claimant_id
            state.claimed_at = db_now
            state.fencing_token = target.fencing_token

            await self._session.flush()

            return AuthorizationClaim(
                state=state,
                fencing_token=target.fencing_token,
            )

        except (
            AuthorizationAlreadyClaimedError,
            AuthorizationExpiredError,
            AuthorizationIntegrityError,
            AuthorizationNotFoundError,
            AuthorizationPersistenceError,
        ):
            raise
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Atomic authorization claim failed."
            ) from exc


    async def transition(
        self,
        authorization_id: UUID,
        target_state: AuthorizationState,
        *,
        claimant_id: str | None = None,
        expected_fencing_token: int | None = None,
        outcome_details: dict[str, Any] | None = None,
    ) -> MigrationAuthorizationState:
        """Atomically transition lifecycle state and update target ownership.

        The caller owns the surrounding transaction.
        UNKNOWN deliberately retains target ownership until reconciliation.
        """

        try:
            identity_result = await self._session.execute(
                select(MigrationAuthorizationState.target_identity).where(
                    MigrationAuthorizationState.id == authorization_id
                )
            )
            target_identity = identity_result.scalar_one_or_none()

            if target_identity is None:
                raise AuthorizationNotFoundError(
                    "Authorization state was not found."
                )

            await self._session.execute(
                pg_insert(MigrationTargetState)
                .values(target_identity=target_identity)
                .on_conflict_do_nothing(
                    index_elements=["target_identity"]
                )
            )

            target_result = await self._session.execute(
                select(MigrationTargetState)
                .where(
                    MigrationTargetState.target_identity == target_identity
                )
                .with_for_update()
            )
            target = target_result.scalar_one()

            auth_result = await self._session.execute(
                select(MigrationAuthorizationState)
                .where(
                    MigrationAuthorizationState.id == authorization_id
                )
                .with_for_update()
            )
            state = auth_result.scalar_one_or_none()

            if state is None:
                raise AuthorizationNotFoundError(
                    "Authorization state was not found."
                )

            if state.target_identity != target_identity:
                raise AuthorizationIntegrityError(
                    "Authorization target identity changed during transition."
                )

            current_state = AuthorizationState(state.status)
            validate_transition(current_state, target_state)

            # ISSUED -> EXPIRED has never acquired target ownership.
            requires_claim = current_state != AuthorizationState.ISSUED

            if requires_claim:
                if (
                    not claimant_id
                    or not claimant_id.strip()
                    or expected_fencing_token is None
                ):
                    raise AuthorizationIntegrityError(
                        "Claimant and fencing token are required."
                    )

                if (
                    target.active_authorization_id != authorization_id
                    or target.active_claimant_id != claimant_id
                    or target.fencing_token != expected_fencing_token
                    or state.claimant_id != claimant_id
                    or state.fencing_token != expected_fencing_token
                ):
                    raise AuthorizationStateConflictError(
                        "Target ownership or fencing token does not match."
                    )

            db_now = await self._session.scalar(
                select(func.clock_timestamp())
            )

            if db_now is None:
                raise AuthorizationPersistenceError(
                    "Database time could not be determined."
                )

            if (
                target_state == AuthorizationState.EXPIRED
                and state.expires_at > db_now
            ):
                raise AuthorizationStateConflictError(
                    "Authorization has not expired yet."
                )

            state.status = target_state.value

            if target_state == AuthorizationState.EXECUTING:
                state.execution_started_at = db_now

            if target_state in {
                AuthorizationState.SUCCEEDED,
                AuthorizationState.FAILED,
                AuthorizationState.EXPIRED,
            }:
                state.completed_at = db_now

            if outcome_details is not None:
                state.outcome_details = {
                    **(state.outcome_details or {}),
                    **outcome_details,
                }

            # UNKNOWN keeps ownership for explicit reconciliation.
            if target_state in {
                AuthorizationState.SUCCEEDED,
                AuthorizationState.FAILED,
                AuthorizationState.EXPIRED,
            } and requires_claim:
                target.active_authorization_id = None
                target.active_claimant_id = None
                target.lease_acquired_at = None

            await self._session.flush()
            return state

        except (
            AuthorizationAlreadyClaimedError,
            AuthorizationExpiredError,
            AuthorizationIntegrityError,
            AuthorizationNotFoundError,
            AuthorizationPersistenceError,
            AuthorizationStateConflictError,
        ):
            raise
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Authorization lifecycle transition failed."
            ) from exc
