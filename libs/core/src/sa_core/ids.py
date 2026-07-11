"""ULID generation and validation.

Hard rule: all platform identifiers are ULIDs — 26-char Crockford base32, lexically
sortable by creation time, safe to mint in a distributed system without coordination.

A ULID is 128 bits: a 48-bit millisecond timestamp followed by 80 random bits. We
implement it directly to keep the shared kernel free of runtime dependencies beyond
pydantic and to make the encoding fully testable.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from sa_core.time import utc_now

# Crockford base32 alphabet (excludes I, L, O, U to avoid transcription errors).
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_DECODE = {char: index for index, char in enumerate(_ALPHABET)}
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

_TIMESTAMP_BITS = 48
_RANDOM_BITS = 80


def _encode(value: int, length: int) -> str:
    chars = [""] * length
    for index in range(length - 1, -1, -1):
        value, remainder = divmod(value, 32)
        chars[index] = _ALPHABET[remainder]
    return "".join(chars)


def new_ulid() -> str:
    """Mint a new ULID for the current instant."""
    timestamp_ms = int(utc_now().timestamp() * 1000)
    randomness = int.from_bytes(os.urandom(_RANDOM_BITS // 8), "big")
    value = (timestamp_ms << _RANDOM_BITS) | randomness
    return _encode(value, 26)


def is_ulid(value: str) -> bool:
    """Return True if the string is a syntactically valid canonical ULID."""
    return bool(_ULID_RE.match(value))


def _decode(value: str) -> int:
    if not is_ulid(value):
        raise ValueError(f"not a valid ULID: {value!r}")
    result = 0
    for char in value:
        result = result * 32 + _DECODE[char]
    return result


def ulid_datetime(value: str) -> datetime:
    """Extract the creation timestamp encoded in a ULID as a UTC datetime."""
    timestamp_ms = _decode(value) >> _RANDOM_BITS
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=utc_now().tzinfo)
