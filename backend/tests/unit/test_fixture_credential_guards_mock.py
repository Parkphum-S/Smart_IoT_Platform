
import asyncio
import importlib.util
import sys
import stat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "rotate_fixture_credential.py"
)

SPEC = importlib.util.spec_from_file_location(
    "fixture_credential_guard_target",
    SCRIPT,
)

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeURL:
    scheme = MODULE.EXPECTED_SCHEME
    path = "/" + MODULE.EXPECTED_DATABASE

    def __init__(self, overrides=None):
        self.overrides = overrides or {}

    def hosts(self):
        host = {
            "host": MODULE.EXPECTED_HOST,
            "port": MODULE.EXPECTED_PORT,
            "username": MODULE.EXPECTED_ROLE,
            "password": "mock-only-password",
        }
        host.update(self.overrides)
        return [host]


def valid_identity():
    return {
        "database_name": MODULE.EXPECTED_DATABASE,
        "current_role": MODULE.EXPECTED_ROLE,
        "session_role": MODULE.EXPECTED_ROLE,
        "server_address": MODULE.EXPECTED_HOST,
        "server_port": MODULE.EXPECTED_PORT,
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


def valid_boundary():
    return {
        "integration_connect": True,
        "production_connect": False,
        "has_effective_memberships": False,
        "has_protected_memberships": False,
    }


def valid_scope():
    return {
        "database_name": MODULE.EXPECTED_DATABASE,
        "current_role": MODULE.EXPECTED_ROLE,
        "session_role": MODULE.EXPECTED_ROLE,
        "production_connect": False,
    }


class FakeConnection:
    def __init__(self, row=None, error=None, close_error=None):
        self.fetchrow = AsyncMock(return_value=row)
        if error:
            self.fetchrow.side_effect = error

        self.close = AsyncMock()
        if close_error:
            self.close.side_effect = close_error

        self.terminate = Mock()


# P1: Runtime Identity

def test_p1_valid_identity():
    connection = FakeConnection(valid_identity())
    assert asyncio.run(
        MODULE.verify_runtime_identity(connection)
    ) is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("database_name", "smart_iot"),
        ("current_role", "postgres"),
        ("session_role", "postgres"),
        ("server_address", "::1"),
        ("server_port", 55432),
        ("is_recovery", True),
        ("production_connect", True),
        ("has_role_memberships", True),
        ("can_login", False),
        ("is_superuser", True),
        ("can_create_database", True),
        ("can_create_role", True),
        ("can_replicate", True),
        ("bypasses_rls", True),
    ],
)
def test_p1_identity_mismatch_fails_closed(field, value):
    row = valid_identity()
    row[field] = value
    connection = FakeConnection(row)

    assert asyncio.run(
        MODULE.verify_runtime_identity(connection)
    ) is False


def test_p1_missing_row_fails_closed():
    connection = FakeConnection(None)
    assert asyncio.run(
        MODULE.verify_runtime_identity(connection)
    ) is False


def test_p1_database_exception_fails_closed():
    connection = FakeConnection(error=RuntimeError("mock failure"))
    assert asyncio.run(
        MODULE.verify_runtime_identity(connection)
    ) is False


# P2: Production Protection

def test_p2_valid_boundary():
    connection = FakeConnection(valid_boundary())
    assert asyncio.run(
        MODULE.verify_production_boundary(connection)
    ) is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("integration_connect", False),
        ("production_connect", True),
        ("has_effective_memberships", True),
        ("has_protected_memberships", True),
    ],
)
def test_p2_boundary_mismatch_fails_closed(field, value):
    row = valid_boundary()
    row[field] = value
    connection = FakeConnection(row)

    assert asyncio.run(
        MODULE.verify_production_boundary(connection)
    ) is False


def test_p2_missing_row_fails_closed():
    connection = FakeConnection(None)
    assert asyncio.run(
        MODULE.verify_production_boundary(connection)
    ) is False


def test_p2_query_exception_fails_closed():
    connection = FakeConnection(error=RuntimeError("mock failure"))
    assert asyncio.run(
        MODULE.verify_production_boundary(connection)
    ) is False


# P3: Connection Lifecycle

def install_mock_asyncpg(monkeypatch, connect):
    fake_asyncpg = SimpleNamespace(connect=connect)
    monkeypatch.setitem(sys.modules, "asyncpg", fake_asyncpg)


def test_p3_invalid_host_rejected_before_connect(monkeypatch):
    connect = AsyncMock()
    install_mock_asyncpg(monkeypatch, connect)

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(
            FakeURL({"host": "192.0.2.10"})
        )
    )

    assert result is False
    connect.assert_not_awaited()


def test_p3_connect_failure_fails_closed(monkeypatch):
    connect = AsyncMock(side_effect=RuntimeError("mock connect failure"))
    install_mock_asyncpg(monkeypatch, connect)

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is False
    connect.assert_awaited_once()


def test_p3_valid_connection_and_cleanup(monkeypatch):
    connection = FakeConnection()
    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    monkeypatch.setattr(
        MODULE,
        "verify_runtime_identity",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        MODULE,
        "verify_production_boundary",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        MODULE,
        "verify_operation_scope",
        AsyncMock(return_value=True),
    )

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is True
    connection.close.assert_awaited_once_with(timeout=5)
    connection.terminate.assert_not_called()


def test_p3_identity_failure_still_closes(monkeypatch):
    connection = FakeConnection()
    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    monkeypatch.setattr(
        MODULE,
        "verify_runtime_identity",
        AsyncMock(return_value=False),
    )

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is False
    connection.close.assert_awaited_once_with(timeout=5)


def test_p3_close_failure_uses_terminate(monkeypatch):
    connection = FakeConnection(
        close_error=RuntimeError("mock close failure")
    )
    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    monkeypatch.setattr(
        MODULE,
        "verify_runtime_identity",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        MODULE,
        "verify_production_boundary",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        MODULE,
        "verify_operation_scope",
        AsyncMock(return_value=True),
    )

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is False
    connection.terminate.assert_called_once()


def test_p3_operation_scope_failure_still_closes(monkeypatch):
    connection = FakeConnection()
    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    identity = AsyncMock(return_value=True)
    boundary = AsyncMock(return_value=True)
    operation_scope = AsyncMock(return_value=False)

    monkeypatch.setattr(MODULE, "verify_runtime_identity", identity)
    monkeypatch.setattr(MODULE, "verify_production_boundary", boundary)
    monkeypatch.setattr(MODULE, "verify_operation_scope", operation_scope)

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is False
    identity.assert_awaited_once_with(connection)
    boundary.assert_awaited_once_with(connection)
    operation_scope.assert_awaited_once_with(connection)
    connection.close.assert_awaited_once_with(timeout=5)
    connection.terminate.assert_not_called()


def test_p3_operation_scope_exception_still_closes(monkeypatch):
    connection = FakeConnection()
    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    monkeypatch.setattr(
        MODULE, "verify_runtime_identity", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        MODULE, "verify_production_boundary", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        MODULE,
        "verify_operation_scope",
        AsyncMock(side_effect=RuntimeError("mock P4 failure")),
    )

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is False
    connection.close.assert_awaited_once_with(timeout=5)
    connection.terminate.assert_not_called()


def test_p3_operation_scope_success_closes(monkeypatch):
    connection = FakeConnection()
    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    monkeypatch.setattr(
        MODULE, "verify_runtime_identity", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        MODULE, "verify_production_boundary", AsyncMock(return_value=True)
    )
    operation_scope = AsyncMock(return_value=True)
    monkeypatch.setattr(MODULE, "verify_operation_scope", operation_scope)

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is True
    operation_scope.assert_awaited_once_with(connection)
    connection.close.assert_awaited_once_with(timeout=5)
    connection.terminate.assert_not_called()


# P4: Single-Role Operation Scope

def test_p4_valid_operation_scope():
    connection = FakeConnection(valid_scope())
    assert asyncio.run(
        MODULE.verify_operation_scope(connection)
    ) is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("database_name", "smart_iot"),
        ("current_role", "postgres"),
        ("session_role", "postgres"),
        ("production_connect", True),
    ],
)
def test_p4_scope_mismatch_fails_closed(field, value):
    row = valid_scope()
    row[field] = value
    connection = FakeConnection(row)

    assert asyncio.run(
        MODULE.verify_operation_scope(connection)
    ) is False


def test_p4_missing_row_fails_closed():
    connection = FakeConnection(None)
    assert asyncio.run(
        MODULE.verify_operation_scope(connection)
    ) is False


def test_p4_exception_fails_closed():
    connection = FakeConnection(error=RuntimeError("mock failure"))
    assert asyncio.run(
        MODULE.verify_operation_scope(connection)
    ) is False


# P5: Error Redaction

def test_p5_error_output_is_redacted(capsys):
    MODULE.report_blocked()
    output = capsys.readouterr().out

    assert "RESULT = BLOCKED" in output
    assert "ERROR_DETAILS = SUPPRESSED" in output
    assert "mock-only-password" not in output


# Execution boundary: source-only inspection

def test_execution_remains_blocked():
    source = SCRIPT.read_text()

    assert 'print("EXECUTION = BLOCKED")' in source
    assert "ALTER ROLE" not in source.upper()


@pytest.mark.parametrize(
    "case",
    [
        "scheme",
        "database",
        "port",
        "username",
        "multiple_hosts",
        "missing_password",
    ],
)
def test_p3_url_validation_rejects_all_invalid_targets(
    monkeypatch, case
):
    connect = AsyncMock()
    install_mock_asyncpg(monkeypatch, connect)

    host = {
        "host": MODULE.EXPECTED_HOST,
        "port": MODULE.EXPECTED_PORT,
        "username": MODULE.EXPECTED_ROLE,
        "password": "mock-only-password",
    }

    url = SimpleNamespace(
        scheme=MODULE.EXPECTED_SCHEME,
        path="/" + MODULE.EXPECTED_DATABASE,
        hosts=lambda: [host],
    )

    if case == "scheme":
        url.scheme = "mysql"
    elif case == "database":
        url.path = "/smart_iot"
    elif case == "port":
        host["port"] = 55432
    elif case == "username":
        host["username"] = "postgres"
    elif case == "multiple_hosts":
        url.hosts = lambda: [host, dict(host)]
    elif case == "missing_password":
        host["password"] = None

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(url)
    )

    assert result is False
    connect.assert_not_awaited()


def test_p3_terminate_failure_fails_closed(monkeypatch):
    connection = FakeConnection(
        close_error=RuntimeError("mock close failure")
    )
    connection.terminate.side_effect = RuntimeError(
        "mock terminate failure"
    )

    connect = AsyncMock(return_value=connection)
    install_mock_asyncpg(monkeypatch, connect)

    monkeypatch.setattr(
        MODULE,
        "verify_runtime_identity",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        MODULE,
        "verify_production_boundary",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        MODULE,
        "verify_operation_scope",
        AsyncMock(return_value=True),
    )

    result = asyncio.run(
        MODULE.verify_connection_lifecycle(FakeURL())
    )

    assert result is False
    connection.close.assert_awaited_once_with(timeout=5)
    connection.terminate.assert_called_once()


# BG-14C-E3-E6-G1: Environment alias and dotenv source validation

def test_g1_environment_names_include_field_and_aliases():
    class FakeSettings:
        model_fields = {
            "database_url": SimpleNamespace(
                alias="DB_URL",
                validation_alias=SimpleNamespace(
                    choices=("DATABASE_URL_ALT", "DB_CONNECTION")
                ),
            ),
            "app_env": SimpleNamespace(
                alias=None,
                validation_alias=None,
            ),
        }

    names = MODULE.get_settings_environment_names(FakeSettings)

    assert names == {
        "database_url",
        "db_url",
        "database_url_alt",
        "db_connection",
        "app_env",
    }


def test_g1_unsupported_alias_fails_closed():
    class FakeSettings:
        model_fields = {
            "database_url": SimpleNamespace(
                alias=None,
                validation_alias=SimpleNamespace(path=("DB_URL", "nested")),
            ),
        }

    with pytest.raises(ValueError):
        MODULE.get_settings_environment_names(FakeSettings)


@pytest.mark.parametrize(
    "config_text",
    [
        "DATABASE_URL=first\nDATABASE_URL=second\n",
        "DATABASE_URL=first\ndatabase_url=second\n",
        "DATABASE_URL\n",
        "DATABASE_URL=first\nINVALID LINE\n",
        "DATABASE_URL=first\nFIXTURE_DATABASE_URL\n",
    ],
)
def test_g1_invalid_dotenv_source_is_rejected(config_text):
    assert MODULE.validate_dotenv_source(config_text) is False


@pytest.mark.parametrize(
    "config_text",
    [
        "DATABASE_URL=postgresql://localhost/test\n",
        "APP_ENV=testing\nDATABASE_URL=postgresql://localhost/test\n",
        "# comment\n\nDATABASE_URL=postgresql://localhost/test\n",
        "EMPTY_VALUE=\nDATABASE_URL=postgresql://localhost/test\n",
    ],
)
def test_g1_valid_dotenv_source_is_accepted(config_text):
    assert MODULE.validate_dotenv_source(config_text) is True



# BG-14C-E3-E6-G2: Directory and file integrity

@pytest.mark.parametrize(
    "uid,gid,mode,system_owned,expected",
    [
        (0, 0, 0o755, True, True),
        (0, 0, 0o775, True, False),
        (0, 0, 0o777, True, False),
        (1000, 1000, 0o755, False, True),
        (1000, 1000, 0o775, False, True),
        (1000, 1000, 0o777, False, False),
        (1000, 1001, 0o755, False, False),
        (1001, 1000, 0o755, False, False),
    ],
)
def test_g2_trusted_directory_metadata_policy(
    uid, gid, mode, system_owned, expected
):
    metadata = SimpleNamespace(
        st_mode=stat.S_IFDIR | mode,
        st_uid=uid,
        st_gid=gid,
    )

    assert MODULE.trusted_directory_metadata(
        metadata,
        1000,
        1000,
        system_owned=system_owned,
    ) is expected


def test_g2_non_directory_metadata_rejected():
    metadata = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o755,
        st_uid=1000,
        st_gid=1000,
    )

    assert MODULE.trusted_directory_metadata(
        metadata, 1000, 1000
    ) is False


def test_g2_directory_chain_rejects_unexpected_path():
    assert MODULE.open_trusted_directory_chain(
        Path("/tmp")
    ) is None


def test_g2_file_metadata_requires_single_hard_link():
    source = SCRIPT.read_text()

    assert "before.st_nlink == 1" in source
    assert "before.st_nlink" in source
    assert "after.st_nlink" in source


def test_g2_directory_open_uses_no_follow_and_dir_fd():
    source = SCRIPT.read_text()

    assert "os.O_DIRECTORY" in source
    assert "os.O_NOFOLLOW" in source
    assert "dir_fd=directory_fd" in source



def test_g2_config_open_is_nonblocking():
    source = SCRIPT.read_text()
    assert "os.O_NONBLOCK" in source
