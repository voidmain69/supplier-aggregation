"""S3RawArchive against a real MinIO (testcontainers). Integration — Docker only.

Proves the raw-archive contract end to end: the bucket is created on demand, a payload is
gzip-compressed under the ``raw/<supplier>/<date>/<id>`` key, and reads back byte-identical.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from connector_brain.adapters.s3_archive import S3RawArchive

pytestmark = pytest.mark.integration

BUCKET = "sa-raw-test"


@pytest.fixture
def s3_client() -> Iterator[Any]:
    from testcontainers.minio import MinioContainer  # noqa: PLC0415

    with MinioContainer() as minio:
        config = minio.get_config()
        client = boto3.client(
            "s3",
            endpoint_url=f"http://{config['endpoint']}",
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"],
            region_name="us-east-1",
        )
        yield client


async def test_store__compressed_payload__is_gzip_and_round_trips(s3_client: Any) -> None:
    archive = S3RawArchive(client=s3_client, bucket=BUCKET)
    await archive.ensure_bucket()

    payload = b'{"status": 1, "result": [{"productID": "100463720"}]}'
    key = await archive.store(
        supplier_code="brain", request_id="01J0000000000000000RAW1", payload=payload
    )

    assert key.startswith("raw/brain/")
    assert key.endswith(".json.gz")
    obj = s3_client.get_object(Bucket=BUCKET, Key=key)
    assert obj["ContentEncoding"] == "gzip"
    assert obj["ContentType"] == "application/json"
    assert gzip.decompress(obj["Body"].read()) == payload


async def test_store__uncompressed__stores_raw_bytes(s3_client: Any) -> None:
    archive = S3RawArchive(client=s3_client, bucket=BUCKET)
    await archive.ensure_bucket()

    payload = b"plain-bytes"
    key = await archive.store(
        supplier_code="brain", request_id="01J0000000000000000RAW2", payload=payload, compress=False
    )

    assert key.endswith(".json")
    obj = s3_client.get_object(Bucket=BUCKET, Key=key)
    assert "ContentEncoding" not in obj or obj.get("ContentEncoding") is None
    assert obj["Body"].read() == payload


async def test_ensure_bucket__called_twice__is_idempotent(s3_client: Any) -> None:
    archive = S3RawArchive(client=s3_client, bucket=BUCKET)
    await archive.ensure_bucket()
    await archive.ensure_bucket()  # must not raise even though the bucket already exists
