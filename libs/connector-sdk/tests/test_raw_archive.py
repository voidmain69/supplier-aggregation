from __future__ import annotations

from sa_connector_sdk.raw_archive import InMemoryRawArchive, build_key
from sa_core.time import utc_now


def test_build_key__scheme_with_date() -> None:
    today = utc_now().date().isoformat()
    key = build_key("brain", "req-123", compressed=True)
    assert key == f"raw/brain/{today}/req-123.json.gz"
    assert build_key("brain", "req-123", compressed=False).endswith("req-123.json")


async def test_in_memory_archive__store_and_get_roundtrip_compressed() -> None:
    archive = InMemoryRawArchive()
    payload = b'{"status": 1, "result": {"productID": 100463720}}'

    key = await archive.store(supplier_code="brain", request_id="req-1", payload=payload)

    assert key.endswith(".json.gz")
    assert archive.objects[key] != payload  # stored compressed
    assert await archive.get(key) == payload  # decompressed on read
    assert archive.content_types[key] == "application/json"


async def test_in_memory_archive__uncompressed() -> None:
    archive = InMemoryRawArchive()
    payload = b"<xml/>"
    key = await archive.store(
        supplier_code="brain",
        request_id="req-2",
        payload=payload,
        content_type="application/xml",
        compress=False,
    )
    assert archive.objects[key] == payload
    assert await archive.get(key) == payload


async def test_in_memory_archive__missing_key_returns_none() -> None:
    assert await InMemoryRawArchive().get("nope") is None
