"""S3/MinIO implementation of the ``RawArchive`` protocol (hard rule 9).

Stores every raw supplier payload under ``raw/<supplier>/<date>/<request_id>.json.gz`` before
normalization, so we can replay parsing after a fix and audit exactly what a supplier returned.
boto3 is synchronous; calls are offloaded to a thread so they never block the event loop.

The client talks plain S3 and works against AWS S3, MinIO or any S3-compatible store via
``endpoint_url``. Bucket credentials are infra secrets (env-injected), not supplier credentials —
those still live in Vault (hard rule 6).
"""

from __future__ import annotations

import asyncio
import gzip
from typing import TYPE_CHECKING, Any

import structlog

from sa_connector_sdk.raw_archive import DEFAULT_CONTENT_TYPE, build_key

if TYPE_CHECKING:
    from connector_brain.settings import Settings

log = structlog.get_logger(__name__)


def build_s3_client(settings: Settings) -> Any:
    """Construct a boto3 S3 client from settings (endpoint set for MinIO/S3-compatible stores)."""
    import boto3  # noqa: PLC0415 -- optional-ish heavy import, kept local to the adapter

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


class S3RawArchive:
    """A :class:`~sa_connector_sdk.raw_archive.RawArchive` backed by S3/MinIO."""

    def __init__(self, *, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def ensure_bucket(self) -> None:
        """Create the bucket if it does not exist yet (idempotent; safe to call on startup)."""
        await asyncio.to_thread(self._create_bucket_if_absent)

    def _create_bucket_if_absent(self) -> None:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
            log.info("raw_archive_bucket_created", bucket=self._bucket)

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
        body = gzip.compress(payload) if compress else payload
        extra = {"ContentEncoding": "gzip"} if compress else {}
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            **extra,
        )
        return key
