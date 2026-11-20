"""Read-only evidence provider for migration authorization recovery."""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncConnection

from app.infrastructure.database.migration_runner import (
    read_alembic_current_heads,
)

from .authorization_revision import (
    MigrationRevisionGraph,
    RevisionContract,
)


class RecoveryRevisionPosition(StrEnum):
    """Observed database revision position on an authorized path."""

    SAME = "SAME"
    BASELINE = "BASELINE"
    EXPECTED = "EXPECTED"
    INTERMEDIATE = "INTERMEDIATE"
    OUTSIDE_PATH = "OUTSIDE_PATH"
    NO_HEADS = "NO_HEADS"
    MULTIPLE_HEADS = "MULTIPLE_HEADS"


@dataclass(frozen=True, slots=True)
class RecoveryEvidence:
    """Immutable revision evidence; does not determine execution outcome."""

    baseline_revision: str
    expected_revision: str
    observed_heads: tuple[str, ...]
    revision_path: tuple[str, ...]
    direction: str
    position: RecoveryRevisionPosition


class RecoveryEvidenceProvider:
    """Collect read-only Alembic revision evidence."""

    def __init__(
        self,
        revision_graph: MigrationRevisionGraph,
        database_role: str,
    ) -> None:
        if not isinstance(revision_graph, MigrationRevisionGraph):
            raise TypeError("A validated migration revision graph is required.")

        if not isinstance(database_role, str) or not database_role.strip():
            raise ValueError("Migration database role is required.")

        self._revision_graph = revision_graph
        self._database_role = database_role

    async def collect(
        self,
        connection: AsyncConnection,
        *,
        baseline_revision: str,
        expected_revision: str,
    ) -> RecoveryEvidence:
        """Collect current revision evidence without changing authorization."""

        contract: RevisionContract = self._revision_graph.bind(
            baseline_revision=baseline_revision,
            expected_revision=expected_revision,
        )

        observed_heads = await read_alembic_current_heads(
            connection,
            self._database_role,
        )

        if len(observed_heads) == 0:
            position = RecoveryRevisionPosition.NO_HEADS

        elif len(observed_heads) > 1:
            position = RecoveryRevisionPosition.MULTIPLE_HEADS

        else:
            current_revision = observed_heads[0]

            if (
                contract.baseline_revision
                == contract.expected_revision
                and current_revision == contract.expected_revision
            ):
                position = RecoveryRevisionPosition.SAME

            elif current_revision == contract.expected_revision:
                position = RecoveryRevisionPosition.EXPECTED

            elif current_revision == contract.baseline_revision:
                position = RecoveryRevisionPosition.BASELINE

            elif current_revision in contract.revision_path:
                position = RecoveryRevisionPosition.INTERMEDIATE

            else:
                position = RecoveryRevisionPosition.OUTSIDE_PATH

        return RecoveryEvidence(
            baseline_revision=contract.baseline_revision,
            expected_revision=contract.expected_revision,
            observed_heads=observed_heads,
            revision_path=contract.revision_path,
            direction=contract.direction,
            position=position,
        )
