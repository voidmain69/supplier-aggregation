"""Map canonical DTOs to platform events (CloudEvents wrapping sa-contracts payloads).

The payload is built through the generated ``sa_contracts`` model, so it is validated
against the source-of-truth schema before it can be enqueued. The event is keyed by the
stable ``supplier_product_id`` (the aggregate id / Kafka partition key).
"""

from __future__ import annotations

from typing import Any

from sa_connector_sdk.dto import RawProduct
from sa_connector_sdk.normalize import content_hash
from sa_contracts import EVENT_REGISTRY
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered
from sa_core.events import OutboxRecord, make_cloud_event

_SOURCE = "//sa/connector-brain"
_DISCOVERED = "supplier.product.discovered"


def product_discovered_record(
    product: RawProduct,
    *,
    supplier_product_id: str,
    supplier_code: str,
    sync_job_id: str,
) -> OutboxRecord:
    """Build the outbox record for a newly discovered supplier product."""
    payload: dict[str, Any] = SupplierProductDiscovered(
        schema_version=1,
        supplier_product_id=supplier_product_id,
        supplier_code=supplier_code,
        external_id=product.external_id,
        external_code=product.external_code,
        articul=product.articul,
        gtin=product.gtin,
        raw_identifiers=product.raw_identifiers,
        name=product.name,
        brand=product.brand,
        supplier_category_id=product.supplier_category_id,
        attributes=product.attributes,
        content_hash=content_hash(product.content_fields()),
        sync_job_id=sync_job_id,
    ).model_dump(mode="json")

    spec = EVENT_REGISTRY[_DISCOVERED]
    envelope = make_cloud_event(
        type=spec.event_type,
        source=_SOURCE,
        subject=supplier_product_id,
        dataschema=spec.dataschema,
        data=payload,
    )
    return OutboxRecord.for_event(topic=spec.topic, envelope=envelope)
