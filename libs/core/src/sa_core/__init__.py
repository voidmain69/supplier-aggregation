"""sa_core — the platform shared kernel.

Pure, dependency-light building blocks every service reuses: ULID identifiers, the
Money value object, GTIN normalization, the RFC 9457 error hierarchy, cursor pagination,
and the CloudEvents/outbox primitives. No I/O, no framework imports.
"""

from __future__ import annotations

from sa_core.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    UpstreamError,
    ValidationError,
)
from sa_core.events import OutboxRecord, make_cloud_event
from sa_core.gtin import compute_check_digit, is_valid_gtin, normalize_gtin
from sa_core.ids import is_ulid, new_ulid, ulid_datetime
from sa_core.money import Money
from sa_core.pagination import Page, decode_cursor, encode_cursor
from sa_core.time import ensure_utc, isoformat, utc_now

__all__ = [
    "AppError",
    "ConflictError",
    "ForbiddenError",
    "Money",
    "NotFoundError",
    "OutboxRecord",
    "Page",
    "RateLimitedError",
    "UnauthorizedError",
    "UpstreamError",
    "ValidationError",
    "compute_check_digit",
    "decode_cursor",
    "encode_cursor",
    "ensure_utc",
    "is_ulid",
    "is_valid_gtin",
    "isoformat",
    "make_cloud_event",
    "new_ulid",
    "normalize_gtin",
    "ulid_datetime",
    "utc_now",
]
