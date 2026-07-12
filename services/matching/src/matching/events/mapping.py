"""Map a confirmed link to a ``matching.link.confirmed`` CloudEvent (via the outbox)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sa_contracts import EVENT_REGISTRY
from sa_contracts.events.matching_link_confirmed import MatchingLinkConfirmed
from sa_core.events import OutboxRecord, make_cloud_event

_SOURCE = "//sa/matching"
_CONFIRMED = "matching.link.confirmed"


def link_confirmed_record(
    *,
    link_id: str,
    supplier_product_id: str,
    canonical_product_id: str,
    method: str,
    confidence: float,
    decided_by: str,
    decided_at: datetime,
) -> OutboxRecord:
    """Build the outbox record for a confirmed supplier→canonical link.

    Keyed by ``supplier_product_id`` (the aggregate id / Kafka partition key).
    """
    payload: dict[str, Any] = MatchingLinkConfirmed(
        schema_version=1,
        link_id=link_id,
        supplier_product_id=supplier_product_id,
        canonical_product_id=canonical_product_id,
        method=method,
        confidence=confidence,
        decided_by=decided_by,
        decided_at=decided_at,
    ).model_dump(mode="json")

    spec = EVENT_REGISTRY[_CONFIRMED]
    envelope = make_cloud_event(
        type=spec.event_type,
        source=_SOURCE,
        subject=supplier_product_id,
        dataschema=spec.dataschema,
        data=payload,
    )
    return OutboxRecord.for_event(topic=spec.topic, envelope=envelope)
