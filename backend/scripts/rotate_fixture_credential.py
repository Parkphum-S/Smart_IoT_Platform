#!/usr/bin/env python3
"""Safely preflight Fixture DB credential rotation.

This version is READ-ONLY.
Credential rotation is deliberately disabled.
"""

import argparse
import os
import stat
import sys
from pathlib import Path


EXPECTED_ROOT = Path(
    "/data/projects/Smart_IoT_Platform/backend"
)
EXPECTED_DATABASE = "smart_iot_integration_test"
EXPECTED_ROLE = "smart_iot_test_fixture"
EXPECTED_HOST = "127.0.0.1"
EXPECTED_PORT = 5432
EXPECTED_SCHEME = "postgresql+asyncpg"


async def verify_runtime_identity(connection) -> bool:
    """Verify the live PostgreSQL session against the fixed target."""
    query = """
        SELECT
            current_database() AS database_name,
            current_user AS current_role,
            session_user AS session_role,
            inet_server_addr()::text AS server_address,
            inet_server_port() AS server_port,
            pg_is_in_recovery() AS is_recovery,
            current_setting('data_directory') AS data_directory,
            has_database_privilege(
                current_user, 'smart_iot', 'CONNECT'
            ) AS production_connect,
            EXISTS (
                SELECT 1
                FROM pg_auth_members
                WHERE member = (
                    SELECT oid
                    FROM pg_roles
                    WHERE rolname = current_user
                )
            ) AS has_role_memberships,
            rol.rolcanlogin AS can_login,
            rol.rolsuper AS is_superuser,
            rol.rolcreatedb AS can_create_database,
            rol.rolcreaterole AS can_create_role,
            rol.rolreplication AS can_replicate,
            rol.rolbypassrls AS bypasses_rls
        FROM pg_roles AS rol
        WHERE rol.rolname = current_user
    """

    try:
        row = await connection.fetchrow(query)

        if row is None:
            return False

        expected = {
            "database_name": EXPECTED_DATABASE,
            "current_role": EXPECTED_ROLE,
            "session_role": EXPECTED_ROLE,
            "server_address": EXPECTED_HOST,
            "server_port": EXPECTED_PORT,
            "is_recovery": False,
            "data_directory": "/data/postgresql/18/main",
            "production_connect": False,
            "has_role_memberships": False,
            "can_login": True,
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": False,
            "can_replicate": False,
            "bypasses_rls": False,
        }

        return all(
            row[key] == value
            for key, value in expected.items()
        )

    except Exception:
        # Do not expose database or credential-related exceptions.
        return False


async def verify_production_boundary(connection) -> bool:
    """Verify database isolation and effective role memberships."""
    query = """
        WITH RECURSIVE granted_roles(role_oid) AS (
            SELECT roleid
            FROM pg_auth_members
            WHERE member = (
                SELECT oid
                FROM pg_roles
                WHERE rolname = 'smart_iot_test_fixture'
            )

            UNION

            SELECT membership.roleid
            FROM pg_auth_members AS membership
            JOIN granted_roles AS granted
              ON membership.member = granted.role_oid
        )
        SELECT
            has_database_privilege(
                'smart_iot_test_fixture',
                'smart_iot_integration_test',
                'CONNECT'
            ) AS integration_connect,
            has_database_privilege(
                'smart_iot_test_fixture',
                'smart_iot',
                'CONNECT'
            ) AS production_connect,
            EXISTS (
                SELECT 1
                FROM granted_roles AS granted
                JOIN pg_roles AS role
                  ON role.oid = granted.role_oid
            ) AS has_effective_memberships,
            EXISTS (
                SELECT 1
                FROM granted_roles AS granted
                JOIN pg_roles AS role
                  ON role.oid = granted.role_oid
                WHERE role.rolname IN (
                    'smart_iot_owner',
                    'smart_iot_test_owner',
                    'smart_iot_test_app'
                )
            ) AS has_protected_memberships
    """

    try:
        row = await connection.fetchrow(query)

        if row is None:
            return False

        return (
            row["integration_connect"] is True
            and row["production_connect"] is False
            and row["has_effective_memberships"] is False
            and row["has_protected_memberships"] is False
        )

    except Exception:
        return False


async def verify_connection_lifecycle(url) -> bool:
    """Run read-only guards after validating the connection target."""
    connection = None
    result = False

    try:
        import asyncpg

        if url.scheme != EXPECTED_SCHEME:
            return False

        if url.path.lstrip("/") != EXPECTED_DATABASE:
            return False

        hosts = url.hosts()
        if len(hosts) != 1:
            return False

        host = hosts[0]

        if host["host"] != EXPECTED_HOST:
            return False

        if host["port"] != EXPECTED_PORT:
            return False

        if host["username"] != EXPECTED_ROLE:
            return False

        if not host["password"]:
            return False

        connection = await asyncpg.connect(
            host=EXPECTED_HOST,
            port=EXPECTED_PORT,
            user=EXPECTED_ROLE,
            password=host["password"],
            database=EXPECTED_DATABASE,
            timeout=5,
        )

        if not await verify_runtime_identity(connection):
            return False

        if not await verify_production_boundary(connection):
            return False

        if not await verify_operation_scope(connection):
            return False

        result = True

    except Exception:
        result = False

    finally:
        if connection is not None:
            try:
                await connection.close(timeout=5)
            except Exception:
                try:
                    connection.terminate()
                except Exception:
                    pass
                result = False

    return result




async def verify_operation_scope(connection) -> bool:
    """Fail closed unless the session is confined to the Fixture target."""
    try:
        row = await connection.fetchrow(
            """
            SELECT
                current_database() AS database_name,
                current_user AS current_role,
                session_user AS session_role,
                has_database_privilege(
                    current_user,
                    'smart_iot',
                    'CONNECT'
                ) AS production_connect
            """
        )

        if row is None:
            return False

        return (
            row["database_name"] == EXPECTED_DATABASE
            and row["current_role"] == EXPECTED_ROLE
            and row["session_role"] == EXPECTED_ROLE
            and row["production_connect"] is False
        )

    except Exception:
        return False


def report_blocked() -> None:
    """Emit a fixed, non-sensitive failure message."""
    print("RESULT = BLOCKED")
    print("ERROR_DETAILS = SUPPRESSED")


def check(condition: bool, label: str) -> bool:
    print(f"{label} = {'PASS' if condition else 'FAIL'}")
    return condition



def get_settings_environment_names(settings_class) -> set[str]:
    """Collect supported environment names, failing closed on unknown aliases."""
    names = set()

    def add_alias(alias):
        if alias is None:
            return

        if isinstance(alias, str):
            names.add(alias.casefold())
            return

        choices = getattr(alias, "choices", None)
        if choices is not None:
            if not choices:
                raise ValueError("Empty validation alias choices")
            for choice in choices:
                add_alias(choice)
            return

        # AliasPath is intentionally rejected: its environment-name
        # interpretation is not established by this preflight.
        raise ValueError("Unsupported Settings alias metadata")

    for field_name, field_info in settings_class.model_fields.items():
        names.add(field_name.casefold())
        add_alias(getattr(field_info, "alias", None))
        add_alias(getattr(field_info, "validation_alias", None))

    return names


def validate_dotenv_source(config_text: str) -> bool:
    """Reject malformed entries, valueless keys and duplicate keys."""
    try:
        import io

        from dotenv.parser import parse_stream

        seen = set()

        for binding in parse_stream(io.StringIO(config_text)):
            if binding.error:
                return False

            if binding.key is None:
                continue

            if binding.value is None:
                return False

            normalized = binding.key.casefold()

            if normalized in seen:
                return False

            seen.add(normalized)

        return True

    except Exception:
        return False



TRUSTED_DIRECTORY_GID = 1000


def trusted_directory_metadata(
    st,
    expected_uid: int,
    expected_gid: int,
    system_owned: bool = False,
) -> bool:
    """Validate one directory under the approved ownership policy."""
    if not stat.S_ISDIR(st.st_mode):
        return False

    mode = stat.S_IMODE(st.st_mode)

    if mode & stat.S_IWOTH:
        return False

    if system_owned:
        return (
            st.st_uid == 0
            and st.st_gid == 0
            and not (mode & stat.S_IWGRP)
        )

    return (
        st.st_uid == expected_uid
        and st.st_gid == expected_gid
    )


def open_trusted_directory_chain(path: Path) -> int | None:
    """Open the approved backend directory without following symlinks."""
    current_fd = None

    try:
        if path != EXPECTED_ROOT or not path.is_absolute():
            return None

        if os.getgid() != TRUSTED_DIRECTORY_GID:
            return None

        flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC
        )

        current_fd = os.open("/", flags)

        if not trusted_directory_metadata(
            os.fstat(current_fd),
            os.getuid(),
            TRUSTED_DIRECTORY_GID,
            system_owned=True,
        ):
            return None

        for index, component in enumerate(path.parts[1:]):
            if component in ("", ".", ".."):
                return None

            next_fd = os.open(
                component,
                flags,
                dir_fd=current_fd,
            )

            previous_fd = current_fd
            current_fd = next_fd
            os.close(previous_fd)

            system_owned = index == 0

            if not trusted_directory_metadata(
                os.fstat(current_fd),
                os.getuid(),
                TRUSTED_DIRECTORY_GID,
                system_owned=system_owned,
            ):
                return None

        result_fd = current_fd
        current_fd = None
        return result_fd

    except Exception:
        return None

    finally:
        if current_fd is not None:
            try:
                os.close(current_fd)
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fixture credential rotation preflight"
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Read-only configuration preflight",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Credential rotation (disabled in this version)",
    )

    args = parser.parse_args()

    if args.execute:
        print("EXECUTION = BLOCKED")
        print("REASON = Execution authorization and final review required")
        return 3

    print("===== FIXTURE CREDENTIAL DRY-RUN =====")
    print("MODE = READ_ONLY")

    root = Path(__file__).resolve().parent.parent
    config_path = root / ".env.integration"

    results = []

    results.append(
        check(root == EXPECTED_ROOT and root.is_dir(),
              "BACKEND_ROOT")
    )

    # Reject environment overrides so the configuration provenance
    # is unambiguous during this preflight.
    protected_overrides = {
        "DATABASE_URL",
        "FIXTURE_DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "MIGRATION_DATABASE_ROLE",
    }

    override_names = [
        name for name in os.environ
        if name.upper() in protected_overrides
    ]

    app_env_names = [
        name for name in os.environ
        if name.upper() == "APP_ENV"
    ]
    app_env = os.environ.get("APP_ENV")
    app_env_valid = (
        not app_env_names
        or (app_env_names == ["APP_ENV"] and app_env == "testing")
    )

    results.append(
        check(not override_names, "DATABASE_ENV_OVERRIDES_ABSENT")
    )

    results.append(
        check(app_env_valid, "APP_ENV_TESTING")
    )

    if not all(results):
        print("RESULT = BLOCKED")
        return 1

    try:
        import io

        from dotenv import dotenv_values

        sys.path.insert(0, str(root))

        from app.core.config import Settings

        settings_environment_names = (
            get_settings_environment_names(Settings)
        )

        environment_overrides = [
            name for name in os.environ
            if name.casefold() in settings_environment_names
        ]

        if environment_overrides:
            print("SETTINGS_ENVIRONMENT_ISOLATION = FAIL")
            print("RESULT = BLOCKED")
            return 1

        directory_fd = open_trusted_directory_chain(root)

        if directory_fd is None:
            print("BACKEND_DIRECTORY_INTEGRITY = FAIL")
            print("RESULT = BLOCKED")
            return 1

        flags = (
            os.O_RDONLY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC
            | os.O_NONBLOCK
        )

        try:
            fd = os.open(
                ".env.integration",
                flags,
                dir_fd=directory_fd,
            )
        finally:
            os.close(directory_fd)

        try:
            before = os.fstat(fd)

            metadata_valid = (
                stat.S_ISREG(before.st_mode)
                and before.st_uid == os.getuid()
                and stat.S_IMODE(before.st_mode) == 0o600
                and before.st_nlink == 1
                and before.st_size <= 1024 * 1024
            )

            if not metadata_valid:
                print("CONFIG_FD_METADATA = FAIL")
                print("RESULT = BLOCKED")
                return 1

            chunks = []

            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)

            after = os.fstat(fd)
            raw_config = b"".join(chunks)

            before_identity = (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_uid,
                before.st_gid,
                before.st_nlink,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )

            after_identity = (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_uid,
                after.st_gid,
                after.st_nlink,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )

            if before_identity != after_identity:
                print("CONFIG_FD_STABILITY = FAIL")
                print("RESULT = BLOCKED")
                return 1

            if len(raw_config) != after.st_size:
                print("CONFIG_FD_SIZE_CHECK = FAIL")
                print("RESULT = BLOCKED")
                return 1

        finally:
            os.close(fd)

        if b"${" in raw_config:
            print("CONFIG_INTERPOLATION = BLOCKED")
            print("RESULT = BLOCKED")
            return 1

        config_text = raw_config.decode("utf-8")

        if not validate_dotenv_source(config_text):
            print("CONFIG_SOURCE_VALIDATION = FAIL")
            print("RESULT = BLOCKED")
            return 1

        parsed = dotenv_values(
            stream=io.StringIO(config_text),
            interpolate=False,
        )

        config_values = {
            key.lower(): value
            for key, value in parsed.items()
            if value is not None
        }

        config_values["app_env"] = "testing"

        settings = Settings(
            _env_file=None,
            **config_values,
        )

        print("CONFIG_FD_OPEN = PASS")
        print("CONFIG_FD_METADATA = PASS")
        print("CONFIG_FD_STABILITY = PASS")
        print("CONFIG_STREAM_PARSE = PASS")
        print("SETTINGS_EXPLICIT_LOAD = PASS")

        url = settings.fixture_database_url

        if url is None:
            print("FIXTURE_URL_PRESENT = FAIL")
            return 1

        hosts = url.hosts()

        url_results = [
            check(url.scheme == EXPECTED_SCHEME, "URL_SCHEME"),
            check(
                url.path.lstrip("/") == EXPECTED_DATABASE,
                "URL_DATABASE",
            ),
            check(len(hosts) == 1, "URL_SINGLE_HOST"),
        ]

        if len(hosts) == 1:
            host = hosts[0]

            url_results.extend([
                check(
                    host["host"] == EXPECTED_HOST,
                    "URL_HOST",
                ),
                check(
                    host["port"] == EXPECTED_PORT,
                    "URL_PORT",
                ),
                check(
                    host["username"] == EXPECTED_ROLE,
                    "URL_ROLE",
                ),
                check(
                    bool(host["password"]),
                    "URL_PASSWORD_PRESENT",
                ),
            ])

        results = url_results

        if not all(results):
            print("RESULT = BLOCKED")
            return 1

        print()
        print("===== SAFETY BOUNDARY =====")
        print("POSTGRES_CONNECTION = NOT_PERFORMED")
        print("PASSWORD_INPUT = NOT_REQUESTED")
        print("LOCK_FILE_CREATED = NO")
        print("TEMPORARY_FILE_CREATED = NO")
        print("CONFIGURATION_MODIFIED = NO")
        print("POSTGRES_ROLE_MODIFIED = NO")
        print("ATOMIC_REPLACEMENT = NOT_PERFORMED")
        print("SECRET_VALUES_DISPLAYED = NO")

        print()
        print("RESULT = DRY_RUN_PREFLIGHT_PASS")
        print("EXECUTION = DISABLED")

        return 0

    except Exception:
        # Never print exception details: they may contain sensitive
        # connection or configuration information.
        report_blocked()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
