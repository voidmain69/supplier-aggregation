"""Opaque cursor pagination (hard rule 7 / api-guidelines).

Offset pagination is forbidden — it is unstable while suppliers sync underneath a
listing. Instead every list endpoint returns an opaque ``next_cursor`` that encodes the
last-seen sort key. Clients treat it as a black box and pass it back verbatim.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from pydantic import BaseModel

from sa_core.errors import ValidationError


def encode_cursor(key: dict[str, Any]) -> str:
    """Encode a sort-key dict into an opaque url-safe cursor string."""
    raw = json.dumps(key, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode a cursor produced by :func:`encode_cursor`.

    Raises :class:`ValidationError` on any tampered or malformed cursor so the caller
    gets a clean 422 rather than a 500.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        decoded = json.loads(raw)
    except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
        raise ValidationError(
            "malformed pagination cursor; omit it to start from the first page",
        ) from exc
    if not isinstance(decoded, dict):
        raise ValidationError("malformed pagination cursor; omit it to start from the first page")
    return decoded


class Page[T](BaseModel):
    """A single page of results plus the cursor to fetch the next one."""

    items: list[T]
    next_cursor: str | None = None
    total_estimate: int | None = None
