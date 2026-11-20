"""Application service coordinating authorization state and audit transactions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .authorization_audit_repository import AuthorizationAuditRepository
from .authorization_repository import AuthorizationStateRepository
from .authorization_state import AuthorizationState
from .authorization_revision import MigrationRevisionGraph


@dataclass(frozen=True, slots=True)
class AuthorizationIssueReceipt:
    """Committed authorization issuance result."""

    authorization_id: UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthorizationClaimReceipt:
    """Committed authorization claim result."""

    authorization_id: UUID
    fencing_token: int


@dataclass(frozen=True, slots=True)
class AuthorizationTransitionReceipt:
    """Committed authorization lifecycle transition result."""

    authorization_id: UUID
    state: AuthorizationState
    fencing_token: int


class AuthorizationService:
    """Coordinate authorization state and audit in one transaction."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._state_repository = AuthorizationStateRepository
        self._audit_repository = AuthorizationAuditRepository

    async def issue(
        self,
        *,
        manifest_digest: str,
        target_identity: str,
        environment: str,
        operation: str,
        policy_version: str,
        baseline_revision: str,
        expected_revision: str,
        revision_graph: MigrationRevisionGraph,
        issued_at: datetime,
        expires_at: datetime,
        outcome_details: dict[str, Any] | None = None,
    ) -> AuthorizationIssueReceipt:
        """Create ISSUED state and its audit event atomically."""

        operation_directions = {
            "MIGRATE": "forward",
            "VERIFY": "same",
            "ROLLBACK": "reverse",
        }

        expected_direction = operation_directions.get(operation)

        if expected_direction is None:
            raise ValueError("Unsupported migration operation.")

        if not isinstance(revision_graph, MigrationRevisionGraph):
            raise TypeError("A validated migration revision graph is required.")

        revision_contract = revision_graph.bind(
            baseline_revision=baseline_revision,
            expected_revision=expected_revision,
        )

        if revision_contract.direction != expected_direction:
            raise ValueError(
                "Migration operation does not match revision direction."
            )

        async with self._session_factory() as session:
            async with session.begin():
                state_repository = self._state_repository(session)
                audit_repository = self._audit_repository()

                state = await state_repository.create(
                    manifest_digest=manifest_digest,
                    target_identity=target_identity,
                    environment=environment,
                    operation=operation,
                    policy_version=policy_version,
                    baseline_revision=baseline_revision,
                    expected_revision=expected_revision,
                    issued_at=issued_at,
                    expires_at=expires_at,
                    outcome_details=outcome_details,
                )

                await audit_repository.record(
                    session,
                    authorization_id=state.id,
                    action="authorization.issued",
                    details={
                        "manifest_digest": manifest_digest,
                        "target_identity": target_identity,
                        "environment": environment,
                        "operation": operation,
                        "policy_version": policy_version,
                        "baseline_revision": baseline_revision,
                        "expected_revision": expected_revision,
                        "revision_direction": revision_contract.direction,
                        "revision_path": list(revision_contract.revision_path),
                    },
                )

                receipt = AuthorizationIssueReceipt(
                    authorization_id=state.id,
                    expires_at=state.expires_at,
                )

            return receipt

    async def claim(
        self,
        authorization_id: UUID,
        *,
        claimant_id: str,
    ) -> AuthorizationClaimReceipt:
        """Claim authorization and persist its audit event atomically."""

        async with self._session_factory() as session:
            async with session.begin():
                state_repository = self._state_repository(session)
                audit_repository = self._audit_repository()

                claim = await state_repository.claim(
                    authorization_id,
                    claimant_id=claimant_id,
                )

                await audit_repository.record(
                    session,
                    authorization_id=authorization_id,
                    action="authorization.claimed",
                    details={
                        "target_identity": claim.state.target_identity,
                        "claimant_id": claimant_id,
                        "fencing_token": claim.fencing_token,
                        "status": claim.state.status,
                    },
                )

                receipt = AuthorizationClaimReceipt(
                    authorization_id=authorization_id,
                    fencing_token=claim.fencing_token,
                )

            return receipt


    async def transition(
        self,
        authorization_id: UUID,
        target_state: AuthorizationState,
        *,
        claimant_id: str | None = None,
        expected_fencing_token: int | None = None,
        outcome_details: dict[str, Any] | None = None,
    ) -> AuthorizationTransitionReceipt:
        """Transition authorization state and audit atomically."""

        audit_actions = {
            AuthorizationState.EXECUTING: "authorization.execution_started",
            AuthorizationState.SUCCEEDED: "authorization.succeeded",
            AuthorizationState.FAILED: "authorization.failed",
            AuthorizationState.UNKNOWN: "authorization.unknown",
            AuthorizationState.EXPIRED: "authorization.expired",
        }

        action = audit_actions.get(target_state)
        if action is None:
            raise ValueError(
                "Use issue() or claim() for ISSUED and CLAIMED transitions."
            )

        async with self._session_factory() as session:
            async with session.begin():
                state_repository = self._state_repository(session)
                audit_repository = self._audit_repository()

                state = await state_repository.transition(
                    authorization_id,
                    target_state,
                    claimant_id=claimant_id,
                    expected_fencing_token=expected_fencing_token,
                    outcome_details=outcome_details,
                )

                audit_details = {
                    "target_identity": state.target_identity,
                    "status": state.status,
                    "fencing_token": state.fencing_token,
                }

                if claimant_id is not None:
                    audit_details["claimant_id"] = claimant_id

                if outcome_details is not None:
                    audit_details["outcome_details"] = outcome_details

                await audit_repository.record(
                    session,
                    authorization_id=authorization_id,
                    action=action,
                    details=audit_details,
                )

                receipt = AuthorizationTransitionReceipt(
                    authorization_id=authorization_id,
                    state=target_state,
                    fencing_token=state.fencing_token,
                )

            return receipt
