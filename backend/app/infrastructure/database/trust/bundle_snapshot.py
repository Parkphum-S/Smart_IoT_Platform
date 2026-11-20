"""Secure, generation-consistent local trusted bundle snapshot reader."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from typing import NoReturn

from pydantic import ValidationError

from .bundle_descriptor import TrustedBundleDescriptor


CURRENT_MAX_BYTES = 129
DESCRIPTOR_MAX_BYTES = 16 * 1024
_READ_CHUNK_SIZE = 64 * 1024

_GENERATION_PATTERN = re.compile(
    rb"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\n?$"
)


class TrustedBundleSnapshotError(ValueError):
    """Raised when a trusted bundle snapshot cannot be read safely."""


@dataclass(frozen=True, slots=True)
class TrustedBundleSnapshot:
    """Raw immutable-bytes snapshot read from exactly one generation."""

    generation_id: str
    descriptor: TrustedBundleDescriptor
    manifest_bytes: bytes
    signature_bytes: bytes
    registry_bytes: bytes


def _reject_constant(value: str) -> NoReturn:
    raise TrustedBundleSnapshotError(
        "non-standard JSON numeric constant rejected"
    )


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in pairs:
        if key in result:
            raise TrustedBundleSnapshotError(
                "duplicate JSON object key rejected"
            )
        result[key] = value

    return result


def _metadata_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _validate_directory(
    fd: int,
    *,
    expected_uid: int | None = None,
    expected_gid: int | None = None,
    expected_device: int | None = None,
    allow_owner_write: bool = False,
) -> os.stat_result:
    metadata = os.fstat(fd)

    if not stat.S_ISDIR(metadata.st_mode):
        raise TrustedBundleSnapshotError(
            "trusted bundle path must be a directory"
        )

    if metadata.st_uid != os.geteuid():
        raise TrustedBundleSnapshotError(
            "trusted directory owner does not match effective user"
        )

    if expected_uid is not None and metadata.st_uid != expected_uid:
        raise TrustedBundleSnapshotError(
            "trusted directory owner mismatch"
        )

    if expected_gid is not None and metadata.st_gid != expected_gid:
        raise TrustedBundleSnapshotError(
            "trusted directory group mismatch"
        )

    if expected_device is not None and metadata.st_dev != expected_device:
        raise TrustedBundleSnapshotError(
            "trusted bundle crosses filesystem boundary"
        )

    forbidden_write_bits = 0o022
    if not allow_owner_write:
        forbidden_write_bits |= 0o200

    if metadata.st_mode & forbidden_write_bits:
        raise TrustedBundleSnapshotError(
            "trusted directory has forbidden write permissions"
        )

    return metadata


def _open_root(path: str) -> int:
    if type(path) is not str or not path or "\x00" in path:
        raise TrustedBundleSnapshotError("invalid trusted bundle root")

    if not os.path.isabs(path):
        raise TrustedBundleSnapshotError(
            "trusted bundle root must be absolute"
        )

    components = path.split("/")[1:]

    if not components or any(
        part in ("", ".", "..") for part in components
    ):
        raise TrustedBundleSnapshotError(
            "trusted bundle root contains invalid components"
        )

    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise TrustedBundleSnapshotError(
            "secure directory-open flags are unavailable"
        )

    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )

    current_fd = -1

    try:
        current_fd = os.open("/", directory_flags)

        for component in components:
            next_fd = os.open(
                component,
                directory_flags,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd

        _validate_directory(current_fd, allow_owner_write=True)

        result = current_fd
        current_fd = -1
        return result

    except TrustedBundleSnapshotError:
        raise
    except OSError as exc:
        raise TrustedBundleSnapshotError(
            "trusted bundle root could not be opened securely"
        ) from exc
    finally:
        if current_fd >= 0:
            os.close(current_fd)


def _open_regular_file(
    directory_fd: int,
    name: str,
    *,
    owner_uid: int,
    owner_gid: int,
    device: int,
    max_bytes: int,
    allow_owner_write: bool = False,
) -> int:
    flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )

    try:
        fd = os.open(name, flags, dir_fd=directory_fd)

        try:
            metadata = os.fstat(fd)

            if not stat.S_ISREG(metadata.st_mode):
                raise TrustedBundleSnapshotError(
                    "trusted bundle entry must be a regular file"
                )

            if metadata.st_nlink != 1:
                raise TrustedBundleSnapshotError(
                    "trusted bundle hard links are rejected"
                )

            if metadata.st_uid != owner_uid:
                raise TrustedBundleSnapshotError(
                    "trusted file owner mismatch"
                )

            if metadata.st_gid != owner_gid:
                raise TrustedBundleSnapshotError(
                    "trusted file group mismatch"
                )

            if metadata.st_dev != device:
                raise TrustedBundleSnapshotError(
                    "trusted file crosses filesystem boundary"
                )

            forbidden_write_bits = 0o022
            if not allow_owner_write:
                forbidden_write_bits |= 0o200

            if metadata.st_mode & forbidden_write_bits:
                raise TrustedBundleSnapshotError(
                    "trusted file has forbidden write permissions"
                )

            if metadata.st_size > max_bytes:
                raise TrustedBundleSnapshotError(
                    "trusted file exceeds size limit"
                )

            return fd

        except Exception:
            os.close(fd)
            raise

    except TrustedBundleSnapshotError:
        raise
    except OSError as exc:
        raise TrustedBundleSnapshotError(
            "trusted bundle file could not be opened securely"
        ) from exc


def _read_file(
    directory_fd: int,
    name: str,
    *,
    owner_uid: int,
    owner_gid: int,
    device: int,
    max_bytes: int,
    allow_owner_write: bool = False,
) -> bytes:
    fd = _open_regular_file(
        directory_fd,
        name,
        owner_uid=owner_uid,
        owner_gid=owner_gid,
        device=device,
        max_bytes=max_bytes,
        allow_owner_write=allow_owner_write,
    )

    try:
        before = os.fstat(fd)
        chunks: list[bytes] = []
        total = 0

        while total <= max_bytes:
            remaining = max_bytes + 1 - total
            chunk = os.read(
                fd,
                min(_READ_CHUNK_SIZE, remaining),
            )

            if not chunk:
                break

            chunks.append(chunk)
            total += len(chunk)

        after = os.fstat(fd)

        if total > max_bytes:
            raise TrustedBundleSnapshotError(
                "trusted file exceeds size limit"
            )

        if _metadata_identity(before) != _metadata_identity(after):
            raise TrustedBundleSnapshotError(
                "trusted file changed during read"
            )

        if total != before.st_size:
            raise TrustedBundleSnapshotError(
                "trusted file size changed during read"
            )

        return b"".join(chunks)

    except TrustedBundleSnapshotError:
        raise
    except OSError as exc:
        raise TrustedBundleSnapshotError(
            "trusted bundle file read failed"
        ) from exc
    finally:
        os.close(fd)


def _read_current(root_fd: int, root_metadata: os.stat_result) -> str:
    raw = _read_file(
        root_fd,
        "CURRENT",
        owner_uid=root_metadata.st_uid,
        owner_gid=root_metadata.st_gid,
        device=root_metadata.st_dev,
        max_bytes=CURRENT_MAX_BYTES,
        allow_owner_write=True,
    )

    if _GENERATION_PATTERN.fullmatch(raw) is None:
        raise TrustedBundleSnapshotError(
            "CURRENT contains an invalid generation ID"
        )

    return raw.rstrip(b"\n").decode("ascii")


def _load_descriptor(raw: bytes) -> TrustedBundleDescriptor:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise TrustedBundleSnapshotError(
            "descriptor UTF-8 BOM is not accepted"
        )

    try:
        decoded = raw.decode("utf-8", errors="strict")
        data = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
        return TrustedBundleDescriptor.model_validate(data)

    except TrustedBundleSnapshotError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
        ValidationError,
        TypeError,
    ) as exc:
        raise TrustedBundleSnapshotError(
            "trusted bundle descriptor is invalid"
        ) from exc


def load_trusted_bundle_snapshot(
    bundle_root: str,
    *,
    max_manifest_bytes: int,
    max_signature_bytes: int,
    max_registry_bytes: int,
) -> TrustedBundleSnapshot:
    """Read CURRENT and all bundle files through pinned directory descriptors.

    The descriptor binds the raw bytes using SHA-256. The trustworthiness
    of this descriptor still depends on the local filesystem trust boundary.
    """
    limits = (
        max_manifest_bytes,
        max_signature_bytes,
        max_registry_bytes,
    )

    if any(type(value) is not int or value < 1 for value in limits):
        raise TrustedBundleSnapshotError(
            "trusted bundle size limits are invalid"
        )

    root_fd = _open_root(bundle_root)
    generations_fd = -1
    generation_fd = -1

    try:
        root_metadata = _validate_directory(
            root_fd,
            allow_owner_write=True,
        )

        generation_id = _read_current(root_fd, root_metadata)

        directory_flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )

        try:
            generations_fd = os.open(
                "generations",
                directory_flags,
                dir_fd=root_fd,
            )

            _validate_directory(
                generations_fd,
                expected_uid=root_metadata.st_uid,
                expected_gid=root_metadata.st_gid,
                expected_device=root_metadata.st_dev,
                allow_owner_write=True,
            )

            generation_fd = os.open(
                generation_id,
                directory_flags,
                dir_fd=generations_fd,
            )

            _validate_directory(
                generation_fd,
                expected_uid=root_metadata.st_uid,
                expected_gid=root_metadata.st_gid,
                expected_device=root_metadata.st_dev,
            )

        except OSError as exc:
            raise TrustedBundleSnapshotError(
                "trusted generation directory could not be opened"
            ) from exc

        descriptor_bytes = _read_file(
            generation_fd,
            "descriptor.json",
            owner_uid=root_metadata.st_uid,
            owner_gid=root_metadata.st_gid,
            device=root_metadata.st_dev,
            max_bytes=DESCRIPTOR_MAX_BYTES,
        )

        descriptor = _load_descriptor(descriptor_bytes)

        if descriptor.generation_id != generation_id:
            raise TrustedBundleSnapshotError(
                "descriptor generation does not match CURRENT"
            )

        manifest_bytes = _read_file(
            generation_fd,
            "manifest.json",
            owner_uid=root_metadata.st_uid,
            owner_gid=root_metadata.st_gid,
            device=root_metadata.st_dev,
            max_bytes=max_manifest_bytes,
        )

        signature_bytes = _read_file(
            generation_fd,
            "signature.json",
            owner_uid=root_metadata.st_uid,
            owner_gid=root_metadata.st_gid,
            device=root_metadata.st_dev,
            max_bytes=max_signature_bytes,
        )

        registry_bytes = _read_file(
            generation_fd,
            "registry.json",
            owner_uid=root_metadata.st_uid,
            owner_gid=root_metadata.st_gid,
            device=root_metadata.st_dev,
            max_bytes=max_registry_bytes,
        )

        digests = (
            (manifest_bytes, descriptor.manifest_sha256),
            (signature_bytes, descriptor.signature_sha256),
            (registry_bytes, descriptor.registry_sha256),
        )

        for raw_data, expected_digest in digests:
            actual_digest = hashlib.sha256(raw_data).hexdigest()

            if actual_digest != expected_digest:
                raise TrustedBundleSnapshotError(
                    "trusted bundle file digest mismatch"
                )

        return TrustedBundleSnapshot(
            generation_id=generation_id,
            descriptor=descriptor,
            manifest_bytes=manifest_bytes,
            signature_bytes=signature_bytes,
            registry_bytes=registry_bytes,
        )

    finally:
        if generation_fd >= 0:
            os.close(generation_fd)

        if generations_fd >= 0:
            os.close(generations_fd)

        os.close(root_fd)
