"""Secure local loading of trusted manifest payloads."""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError

from .trusted_manifest import (
    TrustedManifestPayload,
    validate_manifest_payload,
)


DEFAULT_MAX_MANIFEST_BYTES = 1024 * 1024
_READ_CHUNK_SIZE = 64 * 1024


class ManifestLoadError(ValueError):
    """Raised when a local manifest cannot be loaded safely."""


def _reject_constant(value: str) -> NoReturn:
    raise ManifestLoadError("non-standard JSON numeric constant rejected")


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestLoadError("duplicate JSON object key rejected")
        result[key] = value
    return result


def _open_secure_regular_file(path: str) -> int:
    """Open an absolute path without following symlinks in any component."""
    if not os.path.isabs(path):
        raise ManifestLoadError("manifest path must be absolute")

    components = path.split("/")[1:]
    if not components or any(
        component in ("", ".", "..") for component in components
    ):
        raise ManifestLoadError("manifest path contains invalid components")

    required_flags = ("O_NOFOLLOW", "O_DIRECTORY")
    if any(not hasattr(os, flag) for flag in required_flags):
        raise ManifestLoadError(
            "platform lacks required secure file-open flags"
        )

    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    file_flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )

    directory_fd = -1
    file_fd = -1

    try:
        directory_fd = os.open("/", directory_flags)

        for component in components[:-1]:
            next_fd = os.open(
                component,
                directory_flags,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd

        file_fd = os.open(
            components[-1],
            file_flags,
            dir_fd=directory_fd,
        )

        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ManifestLoadError(
                "manifest path must reference a regular file"
            )

        result_fd = file_fd
        file_fd = -1
        return result_fd

    except ManifestLoadError:
        raise
    except OSError as exc:
        raise ManifestLoadError(
            "manifest file could not be opened securely"
        ) from exc
    finally:
        if file_fd >= 0:
            os.close(file_fd)
        if directory_fd >= 0:
            os.close(directory_fd)


def _read_bounded_file(file_fd: int, max_bytes: int) -> bytes:
    """Read at most max_bytes plus one detection byte."""
    try:
        metadata = os.fstat(file_fd)
        if metadata.st_size > max_bytes:
            raise ManifestLoadError("manifest file exceeds size limit")

        chunks: list[bytes] = []
        total = 0

        while total <= max_bytes:
            remaining = max_bytes + 1 - total
            chunk = os.read(
                file_fd,
                min(_READ_CHUNK_SIZE, remaining),
            )
            if not chunk:
                break

            chunks.append(chunk)
            total += len(chunk)

        if total > max_bytes:
            raise ManifestLoadError("manifest file exceeds size limit")

        return b"".join(chunks)

    except ManifestLoadError:
        raise
    except OSError as exc:
        raise ManifestLoadError("manifest file read failed") from exc


def load_manifest_file(
    path: str | os.PathLike[str],
    *,
    max_bytes: int = DEFAULT_MAX_MANIFEST_BYTES,
    now: datetime | None = None,
) -> TrustedManifestPayload:
    """Load and schema-validate a local manifest without trusting its signature.

    The caller remains responsible for signature verification and for
    obtaining the manifest path from an independently trusted configuration.
    """
    if type(max_bytes) is not int or max_bytes < 1:
        raise ManifestLoadError("max_bytes must be a positive integer")

    try:
        raw_path = os.fspath(path)
    except TypeError as exc:
        raise ManifestLoadError("invalid manifest path type") from exc

    if type(raw_path) is not str or not raw_path:
        raise ManifestLoadError("manifest path must be a nonempty string")

    if "\x00" in raw_path:
        raise ManifestLoadError("manifest path contains NUL")

    file_fd = _open_secure_regular_file(raw_path)
    try:
        raw_data = _read_bounded_file(file_fd, max_bytes)
    finally:
        os.close(file_fd)

    return load_manifest_bytes(
        raw_data,
        max_bytes=max_bytes,
        now=now,
    )


def load_manifest_bytes(
    raw_data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_MANIFEST_BYTES,
    now: datetime | None = None,
) -> TrustedManifestPayload:
    """Parse and validate manifest bytes without filesystem access."""
    if type(max_bytes) is not int or max_bytes < 1:
        raise ManifestLoadError("max_bytes must be a positive integer")

    if type(raw_data) is not bytes:
        raise ManifestLoadError("manifest data must be bytes")

    if len(raw_data) > max_bytes:
        raise ManifestLoadError("manifest data exceeds size limit")

    if raw_data.startswith(b"\xef\xbb\xbf"):
        raise ManifestLoadError("UTF-8 BOM is not accepted")

    try:
        decoded = raw_data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ManifestLoadError("manifest must be valid UTF-8") from exc

    try:
        payload = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except ManifestLoadError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ManifestLoadError("manifest JSON is invalid") from exc

    if not isinstance(payload, dict):
        raise ManifestLoadError("manifest JSON root must be an object")

    try:
        return validate_manifest_payload(payload, now=now)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ManifestLoadError(
            "manifest schema validation failed"
        ) from exc
