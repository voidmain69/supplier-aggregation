"""Normalization helpers connectors use to produce canonical DTOs.

GTIN normalization is delegated to :mod:`sa_core.gtin` (the single source of truth). This
module adds text cleanup, identifier extraction, and a stable content fingerprint used to
emit change events only when a product actually changed.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sa_core.gtin import normalize_gtin

_WS = re.compile(r"\s+")


def normalize_text(value: str | None) -> str | None:
    """Collapse whitespace and strip; return None for empty/None input."""
    if value is None:
        return None
    cleaned = _WS.sub(" ", value).strip()
    return cleaned or None


def extract_gtin(*candidates: str | int | None) -> str | None:
    """Return the first candidate that normalizes to a valid GTIN-14, else None."""
    for candidate in candidates:
        gtin = normalize_gtin(candidate)
        if gtin is not None:
            return gtin
    return None


def content_hash(payload: Any) -> str:
    """Stable SHA-256 over a JSON-serializable payload (key order does not matter)."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
