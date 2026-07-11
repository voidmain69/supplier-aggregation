"""sa_messaging — broker adapters for the platform.

Currently the :class:`KafkaPublisher`, which the outbox relay uses to ship events to
Kafka. Consumer helpers land alongside the first event consumer (catalog).
"""

from __future__ import annotations

from sa_messaging.consumer import EventHandler, KafkaEventConsumer
from sa_messaging.kafka import KafkaPublisher

__all__ = ["EventHandler", "KafkaEventConsumer", "KafkaPublisher"]
