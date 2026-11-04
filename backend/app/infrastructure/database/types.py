"""Shared database type conventions and UTC helpers."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid


def uuid_type() -> Uuid:
    """Return a UUID type using Python UUID objects."""
    return Uuid(as_uuid=True)


def timestamp_type() -> DateTime:
    """Return a timezone-aware timestamp type."""
    return DateTime(timezone=True)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
