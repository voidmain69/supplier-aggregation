"""Event handlers for offer ingestion (idempotent price-changed upsert)."""

from __future__ import annotations

from typing import Any

from sa_messaging import EventHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from offer.adapters.models import ProcessedEvent
from offer.adapters.repository import upsert_offer
from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged


def build_price_changed_handler(
    session_factory: async_sessionmaker[AsyncSession],
) -> EventHandler:
    """Build a handler for ``supplier.offer.price-changed`` bound to a session factory."""

    async def handle(envelope: dict[str, Any]) -> None:
        event_id = envelope["id"]
        payload = SupplierOfferPriceChanged(**envelope["data"])
        async with session_factory() as session, session.begin():
            if await session.get(ProcessedEvent, event_id) is not None:
                return  # already handled — idempotent skip
            await upsert_offer(session, payload)
            session.add(ProcessedEvent(event_id=event_id))

    return handle
