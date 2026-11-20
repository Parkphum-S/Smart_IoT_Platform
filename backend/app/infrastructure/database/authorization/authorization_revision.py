"""Static migration revision graph and authorization contract."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RevisionContract:
    """Immutable baseline-to-expected revision binding."""

    baseline_revision: str
    expected_revision: str
    revision_path: tuple[str, ...]

    direction: str


@dataclass(frozen=True, slots=True)
class MigrationRevisionGraph:
    """Validated linear Alembic revision graph."""

    ordered_revisions: tuple[str, ...]

    @classmethod
    def from_directory(
        cls,
        directory: Path,
    ) -> "MigrationRevisionGraph":
        """Read revision metadata without importing migration scripts."""

        directory = Path(directory)

        if not directory.is_dir():
            raise ValueError("Migration versions directory is invalid.")

        revisions: dict[str, str | None] = {}

        for path in sorted(directory.glob("*.py")):
            metadata = _read_revision_metadata(path)

            if metadata is None:
                continue

            revision, parent = metadata

            if revision in revisions:
                raise ValueError("Duplicate migration revision detected.")

            revisions[revision] = parent

        if not revisions:
            raise ValueError("Migration revision graph is empty.")

        for parent in revisions.values():
            if parent is not None and parent not in revisions:
                raise ValueError("Migration revision parent is missing.")

        roots = [
            revision
            for revision, parent in revisions.items()
            if parent is None
        ]

        if len(roots) != 1:
            raise ValueError("Migration graph must have exactly one root.")

        children: dict[str, list[str]] = {
            revision: [] for revision in revisions
        }

        for revision, parent in revisions.items():
            if parent is not None:
                children[parent].append(revision)

        if any(len(items) > 1 for items in children.values()):
            raise ValueError("Branched migration graphs are not supported.")

        heads = [
            revision
            for revision, items in children.items()
            if not items
        ]

        if len(heads) != 1:
            raise ValueError("Migration graph must have exactly one head.")

        ordered: list[str] = []
        current: str | None = roots[0]

        while current is not None:
            if current in ordered:
                raise ValueError("Migration revision cycle detected.")

            ordered.append(current)
            next_items = children[current]
            current = next_items[0] if next_items else None

        if len(ordered) != len(revisions):
            raise ValueError(
                "Migration graph contains disconnected revisions."
            )

        return cls(ordered_revisions=tuple(ordered))

    def bind(
        self,
        *,
        baseline_revision: str,
        expected_revision: str,
    ) -> RevisionContract:
        """Validate and bind two explicit revisions on this graph."""

        if (
            not isinstance(baseline_revision, str)
            or not baseline_revision.strip()
            or not isinstance(expected_revision, str)
            or not expected_revision.strip()
        ):
            raise ValueError("Baseline and expected revisions are required.")

        try:
            baseline_index = self.ordered_revisions.index(
                baseline_revision
            )
            expected_index = self.ordered_revisions.index(
                expected_revision
            )
        except ValueError as exc:
            raise ValueError(
                "Revision is not present in the validated migration graph."
            ) from exc

        if baseline_index <= expected_index:
            revision_path = self.ordered_revisions[
                baseline_index : expected_index + 1
            ]
        else:
            revision_path = tuple(
                reversed(
                    self.ordered_revisions[
                        expected_index : baseline_index + 1
                    ]
                )
            )

        direction = (
            "same"
            if baseline_index == expected_index
            else (
                "forward"
                if baseline_index < expected_index
                else "reverse"
            )
        )

        return RevisionContract(
            baseline_revision=baseline_revision,
            expected_revision=expected_revision,
            revision_path=tuple(revision_path),
            direction=direction,
        )


def _read_revision_metadata(
    path: Path,
) -> tuple[str, str | None] | None:
    """Extract literal Alembic metadata without executing source code."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        raise ValueError(
            "Unable to parse migration source."
        ) from exc

    metadata: dict[str, Any] = {}

    names = {
        "revision",
        "down_revision",
        "branch_labels",
        "depends_on",
    }

    for node in tree.body:
        name = None
        value_node = None

        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(
                node.targets[0], ast.Name
            ):
                name = node.targets[0].id
                value_node = node.value

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                name = node.target.id
                value_node = node.value

        if name not in names or value_node is None:
            continue

        if name in metadata:
            raise ValueError(
                f"Duplicate {name} declaration in migration source."
            )

        try:
            metadata[name] = ast.literal_eval(value_node)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Non-literal {name} declaration in migration source."
            ) from exc

    if "revision" not in metadata and "down_revision" not in metadata:
        return None

    revision = metadata.get("revision")
    parent = metadata.get("down_revision")

    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("Migration revision identifier is invalid.")

    if parent is not None and (
        not isinstance(parent, str) or not parent.strip()
    ):
        raise ValueError(
            "Multiple-parent or invalid migration revisions are unsupported."
        )

    if metadata.get("branch_labels") is not None:
        raise ValueError("Migration branch labels are unsupported.")

    if metadata.get("depends_on") is not None:
        raise ValueError("Migration revision dependencies are unsupported.")

    return revision, parent
