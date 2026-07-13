"""Map a rebuilt canonical card to a ``catalog.product.updated`` CloudEvent (via the outbox)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sa_contracts import EVENT_REGISTRY
from sa_contracts.events.catalog_product_updated import CatalogProductUpdated
from sa_core.events import OutboxRecord, make_cloud_event

_SOURCE = "//sa/catalog"
_UPDATED = "catalog.product.updated"


def canonical_updated_record(
    *,
    canonical_product_id: str,
    title: str,
    brand: str | None,
    gtin: str | None,
    status: str,
    supplier_product_ids: list[str],
    attributes: dict[str, Any],
    updated_at: datetime,
) -> OutboxRecord:
    """Build the outbox record for a rebuilt canonical product card.

    Keyed by ``canonical_product_id`` (the aggregate id / Kafka partition key).
    """
    payload: dict[str, Any] = CatalogProductUpdated(
        schema_version=1,
        canonical_product_id=canonical_product_id,
        title=title,
        brand=brand,
        gtin=gtin,
        status=status,  # coerced to the Status enum by Pydantic
        supplier_product_ids=supplier_product_ids,
        attributes=attributes,
        updated_at=updated_at,
    ).model_dump(mode="json")

    spec = EVENT_REGISTRY[_UPDATED]
    envelope = make_cloud_event(
        type=spec.event_type,
        source=_SOURCE,
        subject=canonical_product_id,
        dataschema=spec.dataschema,
        data=payload,
    )
    return OutboxRecord.for_event(topic=spec.topic, envelope=envelope)
