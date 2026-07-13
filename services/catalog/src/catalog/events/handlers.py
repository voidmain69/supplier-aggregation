"""Event handlers for catalog ingestion.

The discovered handler upserts the supplier product and records the event id in one
transaction; re-delivery of the same event is a no-op (idempotent, hard rule 3).
"""

from __future__ import annotations

from typing import Any

from sa_messaging import EventHandler
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from catalog.adapters.models import ProcessedEvent
from catalog.adapters.repository import (
    rebuild_canonical_card,
    set_canonical_link,
    upsert_supplier_product,
)
from catalog.events.mapping import canonical_updated_record
from sa_contracts.events.matching_link_confirmed import MatchingLinkConfirmed
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered


async def _rebuild_and_emit(session: AsyncSession, canonical_product_id: str) -> None:
    """Rebuild a canonical's card and stage a ``catalog.product.updated`` event (if it has members).

    No-op when the canonical has no ingested member products yet (nothing to describe).
    """
    result = await rebuild_canonical_card(session, canonical_product_id)
    if result is None:
        return
    canonical, member_ids = result
    enqueue(
        session,
        canonical_updated_record(
            canonical_product_id=canonical.canonical_product_id,
            title=canonical.title,
            brand=canonical.brand,
            gtin=canonical.gtin,
            status=canonical.status,
            supplier_product_ids=member_ids,
            attributes=canonical.attributes,
            updated_at=canonical.updated_at,
        ),
    )


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
            # Rebuild the canonical card and emit catalog.product.updated. On a re-link
            # (merge/split), the previous canonical lost a member, so rebuild it too.
            await _rebuild_and_emit(session, payload.canonical_product_id)
            if payload.previous_canonical_product_id:
                await _rebuild_and_emit(session, payload.previous_canonical_product_id)
            session.add(ProcessedEvent(event_id=event_id))

    return handle
