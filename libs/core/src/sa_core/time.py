"""Timezone-aware UTC time helpers.

Hard rule: timestamps are timezone-aware UTC only. Never construct naive datetimes.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalize a datetime to UTC, rejecting naive datetimes.

    Naive datetimes are ambiguous and forbidden across the platform — the caller
    must attach a timezone at the boundary where the value enters the system.
    """
    if value.tzinfo is None:
        raise ValueError("naive datetime is not allowed; attach a timezone (UTC) at the boundary")
    return value.astimezone(UTC)


def isoformat(value: datetime) -> str:
    """Serialize a datetime as RFC 3339 / ISO 8601 in UTC with a trailing 'Z'."""
    return ensure_utc(value).isoformat().replace("+00:00", "Z")
