"""Fail-closed launcher for Integration Tests.

This launcher configures APP_ENV before starting a fresh pytest process.
It does not connect to databases or modify credentials.
"""

from __future__ import annotations

import os
import subprocess
import stat
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_ROOT = BACKEND_ROOT / "tests" / "integration"


def _path_has_symlink_component(path: Path) -> bool:
    """Return True if any path component is a symlink or cannot be inspected."""
    try:
        absolute = path if path.is_absolute() else Path.cwd() / path
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current = current / part
            try:
                mode = current.lstat().st_mode
            except OSError:
                return True
            if stat.S_ISLNK(mode):
                return True
        return False
    except (OSError, RuntimeError):
        return True


def validate_layout() -> bool:
    """Validate the expected layout without following symlinks."""
    try:
        lexical_root = Path(__file__).absolute().parent.parent
        lexical_tests = lexical_root / "tests"
        lexical_integration = lexical_tests / "integration"
        lexical_pytest_ini = lexical_root / "pytest.ini"

        for candidate in (
            lexical_root,
            lexical_tests,
            lexical_integration,
            lexical_pytest_ini,
        ):
            if _path_has_symlink_component(candidate):
                return False

        root = lexical_root.resolve(strict=True)
        integration = lexical_integration.resolve(strict=True)
        pytest_ini = lexical_pytest_ini.resolve(strict=True)

        if root != BACKEND_ROOT.resolve(strict=True):
            return False
        if not root.is_dir() or not integration.is_dir():
            return False
        if integration != root / "tests" / "integration":
            return False
        if pytest_ini != root / "pytest.ini":
            return False
        if not pytest_ini.is_file():
            return False
        return True
    except (OSError, RuntimeError):
        return False




def validate_arguments(arguments: list[str]) -> bool:
    """Accept only approved options and real paths inside Integration Tests."""
    value_options = {"--tb": {"short", "line", "no"}}
    flag_options = {"-v", "-vv", "-q", "-x", "--exitfirst"}
    expression_options = {"-k", "-m"}

    try:
        if any(
            not isinstance(argument, str)
            or not argument
            or "\x00" in argument
            for argument in arguments
        ):
            return False

        integration_root = INTEGRATION_ROOT.resolve(strict=True)
        index = 0

        while index < len(arguments):
            argument = arguments[index]

            if not isinstance(argument, str) or not argument:
                return False

            if argument in flag_options:
                index += 1
                continue

            if argument in expression_options:
                if index + 1 >= len(arguments):
                    return False
                value = arguments[index + 1]
                if not isinstance(value, str) or not value or value.startswith("-"):
                    return False
                index += 2
                continue

            if argument.startswith("--maxfail="):
                value = argument.split("=", 1)[1]
                if not value.isdecimal() or int(value) < 1:
                    return False
                index += 1
                continue

            if argument == "--maxfail":
                if index + 1 >= len(arguments):
                    return False
                value = arguments[index + 1]
                if not isinstance(value, str) or not value.isdecimal() or int(value) < 1:
                    return False
                index += 2
                continue

            if argument.startswith("--tb="):
                if argument.split("=", 1)[1] not in value_options["--tb"]:
                    return False
                index += 1
                continue

            if argument == "--tb":
                if index + 1 >= len(arguments):
                    return False
                if arguments[index + 1] not in value_options["--tb"]:
                    return False
                index += 2
                continue

            if argument.startswith("-"):
                return False

            candidate = Path(argument)
            if candidate.is_absolute() or ".." in candidate.parts:
                return False

            if (
                len(candidate.parts) < 2
                or candidate.parts[0] != "tests"
                or candidate.parts[1] != "integration"
            ):
                return False

            absolute_candidate = BACKEND_ROOT / candidate
            if _path_has_symlink_component(absolute_candidate):
                return False

            resolved = absolute_candidate.resolve(strict=True)
            try:
                resolved.relative_to(integration_root)
            except ValueError:
                return False

            if not (resolved.is_file() or resolved.is_dir()):
                return False

            index += 1

        return True
    except (OSError, RuntimeError, ValueError):
        return False






def build_child_environment(
    parent_environment: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """Build a restricted environment for the pytest child process."""

    source = os.environ if parent_environment is None else parent_environment

    allowed_keys = (
        "PATH",
        "HOME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
    )

    child_environment: dict[str, str] = {}

    for key in allowed_keys:
        value = source.get(key)

        if value is None:
            continue

        if not isinstance(value, str) or "\x00" in value:
            return None

        if key == "PATH" and not value.strip():
            return None

        child_environment[key] = value

    if "PATH" not in child_environment:
        child_environment["PATH"] = os.defpath

    child_environment["APP_ENV"] = "testing"

    return child_environment


def main(arguments: list[str] | None = None) -> int:
    """Launch pytest with an isolated testing environment."""
    args = list(sys.argv[1:] if arguments is None else arguments)

    if not validate_layout():
        print("RESULT = BLOCKED")
        print("REASON = Integration project layout validation failed")
        return 2

    if not validate_arguments(args):
        print("RESULT = BLOCKED")
        print("REASON = Pytest arguments outside approved scope")
        return 2

    child_env = build_child_environment()

    if child_env is None:
        print("RESULT = BLOCKED")
        print("REASON = Child environment validation failed")
        return 2
    child_env["APP_ENV"] = "testing"

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        str(BACKEND_ROOT / "pytest.ini"),
        str(INTEGRATION_ROOT),
        *args,
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=str(BACKEND_ROOT),
            env=child_env,
            shell=False,
            check=False,
        )
        return completed.returncode
    except (OSError, ValueError):
        print("RESULT = BLOCKED")
        print("REASON = Pytest process could not be started")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
