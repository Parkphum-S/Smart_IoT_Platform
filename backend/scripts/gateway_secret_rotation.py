"""Internal maintenance CLI for gateway-secret key rotation.

Never expose these operations through a public API.
Each batch has its own database session and transaction.
"""

import argparse
import asyncio
import sys
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from app.modules.devices.services.gateway_secret_repository import (
    DeviceGatewaySecretRepository,
)
from app.modules.devices.services.gateway_secret_rotation_service import (
    GatewaySecretRotationService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Internal gateway secret key maintenance"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    rotate = commands.add_parser(
        "rotate",
        help="Rotate one workspace in independently committed batches",
    )
    rotate.add_argument("--workspace-id", required=True)
    rotate.add_argument("--batch-size", type=int, default=100)

    check = commands.add_parser(
        "check-key-usage",
        help="Check whether a key version is still used by stored secrets",
    )
    check.add_argument("--retire-version", required=True)

    return parser


async def rotate_workspace(
    session_factory: async_sessionmaker[AsyncSession],
    service: GatewaySecretRotationService,
    workspace_id: UUID,
    batch_size: int,
    emit: Callable[[str], None] = print,
) -> int:
    """Commit each successful batch independently.

    An exception exits immediately. The active transaction context rolls
    back the failed batch; previously committed batches remain committed.
    """
    total = 0

    while True:
        async with session_factory() as session:
            async with session.begin():
                result = await service.rotate_workspace_batch(
                    session,
                    workspace_id=workspace_id,
                    batch_size=batch_size,
                )

        # The transaction has committed successfully before reporting.
        total += result.rotated_count
        emit(
            f"Batch committed: {result.rotated_count} secret(s); "
            f"total committed: {total}."
        )

        if result.rotated_count == 0:
            break

    return total


def configured_key_versions(settings) -> set[str]:
    """Return configured key versions without exposing key material."""
    if settings.gateway_encryption_keys:
        return set(settings.gateway_encryption_keys)

    if settings.gateway_encryption_key is not None:
        return {settings.gateway_encryption_key_version}

    return set()


async def check_key_retirement(
    session_factory: async_sessionmaker[AsyncSession],
    retire_version: str,
    active_version: str,
    configured_versions: set[str],
    repository: DeviceGatewaySecretRepository | None = None,
) -> int:
    """Return the number of records still encrypted with the retiring key."""
    if retire_version == active_version:
        raise ValueError("The active encryption key cannot be retired.")

    repository = repository or DeviceGatewaySecretRepository()

    async with session_factory() as session:
        counts = await repository.get_key_version_counts(session)

    # Fail closed if the database contains a version absent from configuration.
    missing = set(counts) - configured_versions
    if missing:
        versions = ", ".join(sorted(missing))
        raise RuntimeError(
            "Database contains key versions missing from configuration: "
            + versions
        )

    if retire_version not in configured_versions:
        raise ValueError(
            "The retiring key version must remain configured during the usage check."
        )

    return counts.get(retire_version, 0)


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    engine = create_database_engine(
        str(settings.database_url),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )
    session_factory = create_session_factory(engine)

    try:
        if args.command == "rotate":
            try:
                workspace_id = UUID(args.workspace_id)
            except ValueError as exc:
                raise ValueError("workspace-id must be a valid UUID.") from exc

            if not 1 <= args.batch_size <= 1000:
                raise ValueError("batch-size must be between 1 and 1000.")

            service = GatewaySecretRotationService(settings=settings)

            # Preflight before changing any row in this workspace.
            from app.modules.devices.services.gateway_secret_service import (
                build_gateway_secret_keyring,
            )

            keyring = build_gateway_secret_keyring(settings)
            repository = DeviceGatewaySecretRepository()

            async with session_factory() as session:
                counts = await repository.get_key_version_counts(session)

            missing = set(counts) - keyring.key_versions
            if missing:
                raise RuntimeError(
                    "Database contains key versions unavailable in keyring: "
                    + ", ".join(sorted(missing))
                )

            total = await rotate_workspace(
                session_factory,
                service,
                workspace_id,
                args.batch_size,
            )
            print(f"Rotation complete. Total committed: {total}.")
            return 0

        if args.command == "check-key-usage":
            count = await check_key_retirement(
                session_factory,
                args.retire_version,
                settings.gateway_encryption_key_version,
                configured_key_versions(settings),
            )
            if count:
                print(
                    f"NOT SAFE TO RETIRE: version {args.retire_version} "
                    f"is still used by {count} secret(s)."
                )
                return 2

            print(
                f"No stored secrets use version {args.retire_version}. "
                "The database usage check passed."
            )
            return 0

        raise ValueError("Unsupported command.")
    finally:
        await engine.dispose()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print(
            "Interrupted. Any in-progress batch was rolled back; "
            "previously committed batches remain committed.",
            file=sys.stderr,
        )
        return 130
    except Exception:
        # Do not expose database, configuration, or internal exception details.
        print(
            "ERROR: Gateway secret maintenance failed. "
            "No sensitive details were displayed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
