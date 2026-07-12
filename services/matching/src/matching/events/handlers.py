"""Matching handler on product discovery.

Two passes:
- **Deterministic GTIN**: a valid GTIN auto-links to the canonical for that GTIN
  (creating it on first sight) and emits ``matching.link.confirmed`` immediately.
- **Candidate generation**: no GTIN → score against existing canonicals and stage a
  ``pending_review`` link (to the best match, or to a fresh draft canonical) for an
  operator to confirm/reject. No event is emitted until confirmation.

All in one transaction; idempotent by event id.
"""

from __future__ import annotations

from typing import Any

from sa_messaging import EventHandler
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from matching.adapters.models import ProcessedEvent
from matching.adapters.repository import (
    canonicals_for_matching,
    create_canonical,
    create_link,
    find_canonical_by_gtin,
    get_link,
)
from matching.domain.similarity import similarity
from matching.events.mapping import link_confirmed_record
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

# Minimum lexical score to suggest an existing canonical instead of proposing a new one.
CANDIDATE_THRESHOLD = 0.5


async def _gtin_auto_link(
    session: AsyncSession, product: SupplierProductDiscovered, gtin: str
) -> None:
    canonical = await find_canonical_by_gtin(session, gtin)
    if canonical is None:
        canonical = create_canonical(session, gtin=gtin, brand=product.brand, title=product.name)
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


async def _stage_candidate(session: AsyncSession, product: SupplierProductDiscovered) -> None:
    candidates = await canonicals_for_matching(session, brand=product.brand)
    best_id: str | None = None
    best_score = 0.0
    for candidate in candidates:
        score = similarity(product.name, product.brand, candidate.title, candidate.brand)
        if score > best_score:
            best_id, best_score = candidate.canonical_product_id, score

    if best_id is not None and best_score >= CANDIDATE_THRESHOLD:
        canonical_product_id = best_id
    else:
        draft = create_canonical(
            session, gtin=None, brand=product.brand, title=product.name, status="draft"
        )
        canonical_product_id = draft.canonical_product_id

    create_link(
        session,
        supplier_product_id=product.supplier_product_id,
        canonical_product_id=canonical_product_id,
        method="rag_suggested",
        confidence=best_score,
        status="pending_review",
        decided_by="system",
    )
    # no event yet — waits for an operator to confirm (see the curation API)


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
            if await get_link(session, product.supplier_product_id) is not None:
                return  # already linked or queued

            if product.gtin is not None:
                await _gtin_auto_link(session, product, product.gtin)
            else:
                await _stage_candidate(session, product)

    return handle
