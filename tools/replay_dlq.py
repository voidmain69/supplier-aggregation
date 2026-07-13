"""Replay dead-lettered events back onto their original topic.

Reads messages from a dead-letter topic (``sa.dlq.<topic>``), strips the DLQ bookkeeping
headers, and re-publishes each message verbatim to its original topic (from the
``x-original-topic`` header, falling back to the ``sa.dlq.`` prefix stripped off). Offsets are
committed only after a successful re-publish, so an interrupted run resumes without loss.

Usage:
    uv run python tools/replay_dlq.py --bootstrap localhost:19092 --topic sa.dlq.sa.supplier.offer
    uv run python tools/replay_dlq.py --bootstrap ... --topic sa.dlq.sa.supplier.offer --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sa_messaging.consumer import DLQ_TOPIC_PREFIX

_DLQ_HEADERS = frozenset({"x-failure-reason", "x-attempts", "x-original-topic"})


def _original_topic(dlq_topic: str, headers: list[tuple[str, bytes]]) -> str:
    for key, value in headers:
        if key == "x-original-topic":
            return value.decode("utf-8")
    if dlq_topic.startswith(DLQ_TOPIC_PREFIX):
        return dlq_topic[len(DLQ_TOPIC_PREFIX) :]
    raise ValueError(
        f"cannot determine original topic for {dlq_topic!r} (no x-original-topic header)"
    )


def _forward_headers(headers: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    return [(k, v) for k, v in headers if k not in _DLQ_HEADERS]


async def replay(
    *, bootstrap: str, topic: str, group: str, max_messages: int | None, dry_run: bool, idle_ms: int
) -> int:
    """Drain `topic`, re-publishing each message to its original topic. Returns count replayed."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap, acks="all")
    replayed = 0
    await consumer.start()
    await producer.start()
    try:
        while max_messages is None or replayed < max_messages:
            batch = await consumer.getmany(timeout_ms=idle_ms, max_records=1)
            if not batch:
                break  # idle: no more dead letters waiting
            for records in batch.values():
                for record in records:
                    headers = [(k, bytes(v)) for k, v in (record.headers or [])]
                    target = _original_topic(topic, headers)
                    print(f"replay {topic} -> {target} key={record.key!r}")
                    if not dry_run:
                        await producer.send_and_wait(
                            target,
                            value=record.value,
                            key=record.key,
                            headers=_forward_headers(headers),
                        )
                        await consumer.commit()
                    replayed += 1
                    if max_messages is not None and replayed >= max_messages:
                        break
    finally:
        await consumer.stop()
        await producer.stop()
    return replayed


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay dead-lettered events to their origin topic."
    )
    parser.add_argument("--bootstrap", required=True, help="Kafka bootstrap servers.")
    parser.add_argument("--topic", required=True, help="Dead-letter topic, e.g. sa.dlq.<topic>.")
    parser.add_argument("--group", default="dlq-replay", help="Consumer group for the replay run.")
    parser.add_argument(
        "--max", type=int, default=None, help="Stop after N messages (default: all)."
    )
    parser.add_argument("--dry-run", action="store_true", help="List without re-publishing.")
    parser.add_argument("--idle-ms", type=int, default=5000, help="Stop after this idle gap (ms).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    replayed = asyncio.run(
        replay(
            bootstrap=args.bootstrap,
            topic=args.topic,
            group=args.group,
            max_messages=args.max,
            dry_run=args.dry_run,
            idle_ms=args.idle_ms,
        )
    )
    print(f"replayed {replayed} message(s)" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
