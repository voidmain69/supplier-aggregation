"""Map an effective-price change to an ``offer.effective-price.changed`` event (via the outbox)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from sa_contracts import EVENT_REGISTRY
from sa_contracts.events.offer_effective_price_changed import OfferEffectivePriceChanged
from sa_core.events import OutboxRecord, make_cloud_event

_SOURCE = "//sa/offer"
_TYPE = "offer.effective-price.changed"

Cause = Literal["price_changed", "terms_changed"]


def _money(value: Decimal | None) -> str | None:
    return f"{value:.4f}" if value is not None else None


def effective_price_changed_record(
    *,
    offer_id: str,
    supplier_account_id: str,
    supplier_product_id: str,
    old_effective: Decimal | None,
    new_effective: Decimal,
    base_price: Decimal,
    currency: str,
    observed_at: datetime,
    cause: Cause,
) -> OutboxRecord:
    """Build the outbox record for an effective-price change, keyed by ``offer_id``."""
    payload: dict[str, Any] = OfferEffectivePriceChanged(
        schema_version=1,
        offer_id=offer_id,
        supplier_account_id=supplier_account_id,
        supplier_product_id=supplier_product_id,
        old_effective_price_uah=_money(old_effective),
        new_effective_price_uah=f"{new_effective:.4f}",
        base_price=f"{base_price:.4f}",
        currency=currency,
        observed_at=observed_at,
        cause=cause,
    ).model_dump(mode="json")

    spec = EVENT_REGISTRY[_TYPE]
    envelope = make_cloud_event(
        type=spec.event_type,
        source=_SOURCE,
        subject=offer_id,
        dataschema=spec.dataschema,
        data=payload,
    )
    return OutboxRecord.for_event(topic=spec.topic, envelope=envelope)
