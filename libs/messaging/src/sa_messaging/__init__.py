"""sa_messaging — broker adapters for the platform.

Currently the :class:`KafkaPublisher`, which the outbox relay uses to ship events to
Kafka. Consumer helpers land alongside the first event consumer (catalog).
"""

from __future__ import annotations

from sa_messaging.consumer import (
    DeadLetterSink,
    EventHandler,
    KafkaEventConsumer,
    dlq_topic_for,
)
from sa_messaging.kafka import KafkaPublisher

__all__ = [
    "DeadLetterSink",
    "EventHandler",
    "KafkaEventConsumer",
    "KafkaPublisher",
    "dlq_topic_for",
]
