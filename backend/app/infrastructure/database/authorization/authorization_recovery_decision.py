"""Fail-closed decision contract for migration recovery evidence."""

from dataclasses import dataclass
from enum import StrEnum

from .authorization_recovery_evidence import (
    RecoveryEvidence,
    RecoveryRevisionPosition,
)


class RecoveryDecision(StrEnum):
    """Permitted recovery evaluation outcomes."""

    UNRESOLVED = "UNRESOLVED"


class RecoveryDecisionReason(StrEnum):
    """Machine-readable reasons for unresolved recovery."""

    EXPECTED_REVISION_WITHOUT_EXECUTION_PROOF = (
        "EXPECTED_REVISION_WITHOUT_EXECUTION_PROOF"
    )
    BASELINE_WITHOUT_FAILURE_PROOF = (
        "BASELINE_WITHOUT_FAILURE_PROOF"
    )
    INTERMEDIATE_REVISION = "INTERMEDIATE_REVISION"
    SAME_REVISION_WITHOUT_EXECUTION_PROOF = (
        "SAME_REVISION_WITHOUT_EXECUTION_PROOF"
    )
    REVISION_OUTSIDE_AUTHORIZED_PATH = (
        "REVISION_OUTSIDE_AUTHORIZED_PATH"
    )
    NO_REVISION_HEADS = "NO_REVISION_HEADS"
    MULTIPLE_REVISION_HEADS = "MULTIPLE_REVISION_HEADS"


@dataclass(frozen=True, slots=True)
class RecoveryDecisionResult:
    """Immutable recovery evaluation result."""

    decision: RecoveryDecision
    reason: RecoveryDecisionReason
    evidence_position: RecoveryRevisionPosition


def evaluate_recovery_evidence(
    evidence: RecoveryEvidence,
) -> RecoveryDecisionResult:
    """Validate revision evidence and return a fail-closed decision.

    Current Alembic heads alone cannot prove execution success or failure.
    Therefore this contract never terminalizes an authorization.
    """

    if not isinstance(evidence, RecoveryEvidence):
        raise TypeError("Validated recovery evidence is required.")

    if (
        not evidence.baseline_revision
        or not evidence.expected_revision
        or not evidence.revision_path
    ):
        raise ValueError("Recovery revision contract is incomplete.")

    if (
        evidence.revision_path[0] != evidence.baseline_revision
        or evidence.revision_path[-1] != evidence.expected_revision
        or len(set(evidence.revision_path)) != len(evidence.revision_path)
    ):
        raise ValueError("Recovery revision path is inconsistent.")

    if evidence.direction not in {"forward", "reverse", "same"}:
        raise ValueError("Recovery revision direction is invalid.")

    if (
        evidence.direction == "same"
    ) != (
        evidence.baseline_revision == evidence.expected_revision
    ):
        raise ValueError("Recovery revision direction does not match binding.")

    if not isinstance(evidence.observed_heads, tuple):
        raise TypeError("Observed revision heads must be immutable.")

    if any(
        not isinstance(head, str) or not head.strip()
        for head in evidence.observed_heads
    ):
        raise ValueError("Observed revision head is invalid.")

    if len(evidence.observed_heads) == 0:
        expected_position = RecoveryRevisionPosition.NO_HEADS

    elif len(evidence.observed_heads) > 1:
        expected_position = RecoveryRevisionPosition.MULTIPLE_HEADS

    else:
        current = evidence.observed_heads[0]

        if current == evidence.expected_revision:
            expected_position = (
                RecoveryRevisionPosition.SAME
                if evidence.direction == "same"
                else RecoveryRevisionPosition.EXPECTED
            )
        elif current == evidence.baseline_revision:
            expected_position = RecoveryRevisionPosition.BASELINE
        elif current in evidence.revision_path:
            expected_position = RecoveryRevisionPosition.INTERMEDIATE
        else:
            expected_position = RecoveryRevisionPosition.OUTSIDE_PATH

    if evidence.position != expected_position:
        raise ValueError("Recovery evidence position is inconsistent.")

    reasons = {
        RecoveryRevisionPosition.EXPECTED:
            RecoveryDecisionReason.EXPECTED_REVISION_WITHOUT_EXECUTION_PROOF,
        RecoveryRevisionPosition.BASELINE:
            RecoveryDecisionReason.BASELINE_WITHOUT_FAILURE_PROOF,
        RecoveryRevisionPosition.INTERMEDIATE:
            RecoveryDecisionReason.INTERMEDIATE_REVISION,
        RecoveryRevisionPosition.SAME:
            RecoveryDecisionReason.SAME_REVISION_WITHOUT_EXECUTION_PROOF,
        RecoveryRevisionPosition.OUTSIDE_PATH:
            RecoveryDecisionReason.REVISION_OUTSIDE_AUTHORIZED_PATH,
        RecoveryRevisionPosition.NO_HEADS:
            RecoveryDecisionReason.NO_REVISION_HEADS,
        RecoveryRevisionPosition.MULTIPLE_HEADS:
            RecoveryDecisionReason.MULTIPLE_REVISION_HEADS,
    }

    return RecoveryDecisionResult(
        decision=RecoveryDecision.UNRESOLVED,
        reason=reasons[expected_position],
        evidence_position=expected_position,
    )
