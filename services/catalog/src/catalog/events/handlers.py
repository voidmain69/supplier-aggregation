"""Event handlers for catalog ingestion.

The discovered handler upserts the supplier product and records the event id in one
transaction; re-delivery of the same event is a no-op (idempotent, hard rule 3).
"""

from __future__ import annotations

from typing import Any

from sa_messaging import EventHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from catalog.adapters.models import ProcessedEvent
from catalog.adapters.repository import set_canonical_link, upsert_supplier_product
from sa_contracts.events.matching_link_confirmed import MatchingLinkConfirmed
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered


def build_discovered_handler(
    session_factory: async_sessionmaker[AsyncSession],
) -> EventHandler:
    """Build a handler for ``supplier.product.discovered`` bound to a session factory."""

    async def handle(envelope: dict[str, Any]) -> None:
        event_id = envelope["id"]
        payload = SupplierProductDiscovered(**envelope["data"])
        async with session_factory() as session, session.begin():
            if await session.get(ProcessedEvent, event_id) is not None:
                return  # already handled — idempotent skip
            await upsert_supplier_product(session, payload)
            session.add(ProcessedEvent(event_id=event_id))

    return handle


def build_link_confirmed_handler(
    session_factory: async_sessionmaker[AsyncSession],
) -> EventHandler:
    """Build a handler for ``matching.link.confirmed`` that records the canonical mapping."""

    async def handle(envelope: dict[str, Any]) -> None:
        event_id = envelope["id"]
        payload = MatchingLinkConfirmed(**envelope["data"])
        async with session_factory() as session, session.begin():
            if await session.get(ProcessedEvent, event_id) is not None:
                return  # already handled — idempotent skip
            await set_canonical_link(
                session,
                supplier_product_id=payload.supplier_product_id,
                canonical_product_id=payload.canonical_product_id,
            )
            session.add(ProcessedEvent(event_id=event_id))

    return handle
