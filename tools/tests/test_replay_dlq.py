"""Tests for tools/replay_dlq.py — the dead-letter replay tool.

The tool is a standalone script (tools/ is not a package), so it is loaded by path.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "replay_dlq.py"
_spec = importlib.util.spec_from_file_location("replay_dlq", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
replay_dlq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay_dlq)


def test_original_topic__prefers_header() -> None:
    headers = [("x-original-topic", b"sa.supplier.offer"), ("ce-id", b"1")]
    assert replay_dlq._original_topic("sa.dlq.whatever", headers) == "sa.supplier.offer"


def test_original_topic__falls_back_to_prefix_strip() -> None:
    assert replay_dlq._original_topic("sa.dlq.sa.supplier.offer", []) == "sa.supplier.offer"


def test_original_topic__unknown__raises() -> None:
    with pytest.raises(ValueError, match="cannot determine original topic"):
        replay_dlq._original_topic("not-a-dlq-topic", [])


def test_forward_headers__drops_dlq_bookkeeping() -> None:
    headers = [
        ("ce-id", b"1"),
        ("x-failure-reason", b"boom"),
        ("x-attempts", b"3"),
        ("x-original-topic", b"t"),
    ]
    assert replay_dlq._forward_headers(headers) == [("ce-id", b"1")]


@pytest.mark.integration
def test_replay__moves_message_back_to_original_topic() -> None:
    from testcontainers.kafka import KafkaContainer  # noqa: PLC0415

    origin = "sa.supplier.offer"
    dlq = f"sa.dlq.{origin}"

    with KafkaContainer() as kafka:
        bootstrap = kafka.get_bootstrap_server()
        asyncio.run(_seed_dlq(bootstrap, dlq, origin))

        replayed = asyncio.run(
            replay_dlq.replay(
                bootstrap=bootstrap,
                topic=dlq,
                group="dlq-replay-test",
                max_messages=None,
                dry_run=False,
                idle_ms=4000,
            )
        )
        assert replayed == 1

        record = asyncio.run(_read_one(bootstrap, origin))
        assert record.value == b'{"id":"evt-1"}'
        headers = dict(record.headers)
        assert b"x-failure-reason" not in headers  # bookkeeping stripped on replay
        assert headers["ce-id"] == b"1"


async def _seed_dlq(bootstrap: str, dlq_topic: str, origin: str) -> None:
    from aiokafka import AIOKafkaProducer  # noqa: PLC0415

    producer = AIOKafkaProducer(bootstrap_servers=bootstrap, acks="all")
    await producer.start()
    try:
        await producer.send_and_wait(
            dlq_topic,
            value=b'{"id":"evt-1"}',
            key=b"agg-1",
            headers=[
                ("ce-id", b"1"),
                ("x-failure-reason", b"boom"),
                ("x-attempts", b"3"),
                ("x-original-topic", origin.encode()),
            ],
        )
    finally:
        await producer.stop()


async def _read_one(bootstrap: str, topic: str):  # type: ignore[no-untyped-def]
    from aiokafka import AIOKafkaConsumer  # noqa: PLC0415

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id="origin-reader",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        return await asyncio.wait_for(consumer.getone(), timeout=30)
    finally:
        await consumer.stop()
