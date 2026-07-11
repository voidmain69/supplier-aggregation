"""CloudEvents envelope builder and transactional outbox record.

Hard rule 3: events are published only via the transactional outbox. Producers build a
CloudEvent with :func:`make_cloud_event`, persist it as an :class:`OutboxRecord` inside
the same DB transaction as their business write, and a relay ships it to Kafka. This
module owns the envelope shape (contracts/events/_envelope.json) so every producer emits
identical structure.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sa_core.ids import new_ulid
from sa_core.time import isoformat, utc_now

SPEC_VERSION = "1.0"


def make_cloud_event(
    *,
    type: str,
    source: str,
    subject: str,
    data: dict[str, Any],
    dataschema: str,
    traceparent: str | None = None,
) -> dict[str, Any]:
    """Build a CloudEvents 1.0 envelope.

    ``source`` is the producing service (e.g. ``//sa/connector-brain``), ``subject`` is
    the aggregate id used as the Kafka partition key, and ``dataschema`` is the URI of
    the JSON Schema that ``data`` validates against. The event ``id`` is a fresh ULID.
    """
    envelope: dict[str, Any] = {
        "specversion": SPEC_VERSION,
        "id": new_ulid(),
        "source": source,
        "type": type,
        "time": isoformat(utc_now()),
        "subject": subject,
        "dataschema": dataschema,
        "data": data,
    }
    if traceparent is not None:
        envelope["traceparent"] = traceparent
    return envelope


class OutboxRecord(BaseModel):
    """A pending event row in a service's ``outbox`` table.

    Written in the same transaction as the business change; the relay reads unsent rows,
    publishes ``envelope`` to ``topic`` keyed by ``key``, then stamps ``sent_at``.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_ulid)
    topic: str
    key: str
    envelope: dict[str, Any]

    @classmethod
    def for_event(cls, *, topic: str, envelope: dict[str, Any]) -> OutboxRecord:
        """Create an outbox record from a CloudEvent, keyed by the event subject."""
        return cls(id=envelope["id"], topic=topic, key=envelope["subject"], envelope=envelope)
