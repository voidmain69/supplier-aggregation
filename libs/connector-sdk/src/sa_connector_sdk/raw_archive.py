"""Raw payload archive (hard rule 9): store supplier responses before normalization.

Archiving the raw response lets us replay normalization after a bug fix and audit exactly
what a supplier returned. This defines the :class:`RawArchive` protocol and an in-memory
implementation for tests; each connector service ships the S3/MinIO implementation (see
``connector_brain.adapters.s3_archive``) so boto3 stays out of this lightweight SDK.
"""

from __future__ import annotations

import gzip
from typing import Protocol

from sa_core.time import utc_now

DEFAULT_CONTENT_TYPE = "application/json"


def build_key(supplier_code: str, request_id: str, *, compressed: bool) -> str:
    """Build the object key: ``raw/<supplier>/<yyyy-mm-dd>/<request_id>[.json][.gz]``."""
    date = utc_now().date().isoformat()
    suffix = ".json.gz" if compressed else ".json"
    return f"raw/{supplier_code}/{date}/{request_id}{suffix}"


class RawArchive(Protocol):
    """Stores an immutable raw supplier payload and returns its storage key."""

    async def store(
        self,
        *,
        supplier_code: str,
        request_id: str,
        payload: bytes,
        content_type: str = DEFAULT_CONTENT_TYPE,
        compress: bool = True,
    ) -> str: ...


class InMemoryRawArchive:
    """A :class:`RawArchive` backed by a dict — for tests and local runs."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    async def store(
        self,
        *,
        supplier_code: str,
        request_id: str,
        payload: bytes,
        content_type: str = DEFAULT_CONTENT_TYPE,
        compress: bool = True,
    ) -> str:
        key = build_key(supplier_code, request_id, compressed=compress)
        self.objects[key] = gzip.compress(payload) if compress else payload
        self.content_types[key] = content_type
        return key

    async def get(self, key: str) -> bytes | None:
        """Return the stored bytes (decompressed) for a key, or None if absent."""
        blob = self.objects.get(key)
        if blob is None:
            return None
        return gzip.decompress(blob) if key.endswith(".gz") else blob
