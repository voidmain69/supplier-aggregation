"""Matching handler: deterministic GTIN auto-link on product discovery.

On ``supplier.product.discovered``: if the product has a valid GTIN, link it to the
canonical product with that GTIN (creating the canonical on first sight) and emit
``matching.link.confirmed`` via the outbox — all in one transaction. Products without a
GTIN are left for the RAG + human-curation pass (a follow-up). Idempotent by event id.
"""

from __future__ import annotations

from typing import Any

from sa_messaging import EventHandler
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from matching.adapters.models import ProcessedEvent
from matching.adapters.repository import (
    create_canonical,
    create_link,
    find_canonical_by_gtin,
    get_link,
)
from matching.events.mapping import link_confirmed_record
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered


def build_discovered_handler(
    session_factory: async_sessionmaker[AsyncSession],
) -> EventHandler:
    """Build the ``supplier.product.discovered`` handler bound to a session factory."""

    async def handle(envelope: dict[str, Any]) -> None:
        event_id = envelope["id"]
        product = SupplierProductDiscovered(**envelope["data"])
        async with session_factory() as session, session.begin():
            if await session.get(ProcessedEvent, event_id) is not None:
                return  # already handled
            session.add(ProcessedEvent(event_id=event_id))

            if product.gtin is None:
                return  # deterministic pass only; no GTIN -> handled by RAG/curation later
            if await get_link(session, product.supplier_product_id) is not None:
                return  # already linked

            canonical = await find_canonical_by_gtin(session, product.gtin)
            if canonical is None:
                canonical = create_canonical(
                    session, gtin=product.gtin, brand=product.brand, title=product.name
                )
            link = create_link(
                session,
                supplier_product_id=product.supplier_product_id,
                canonical_product_id=canonical.canonical_product_id,
                method="gtin_auto",
                confidence=1.0,
                status="auto",
                decided_by="system",
            )
            enqueue(
                session,
                link_confirmed_record(
                    link_id=link.link_id,
                    supplier_product_id=link.supplier_product_id,
                    canonical_product_id=link.canonical_product_id,
                    method="gtin_auto",
                    confidence=1.0,
                    decided_by="system",
                    decided_at=link.decided_at,
                ),
            )

    return handle
