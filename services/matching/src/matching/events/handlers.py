"""Matching handler on product discovery.

Two passes:
- **Deterministic GTIN**: a valid GTIN auto-links to the canonical for that GTIN
  (creating it on first sight) and emits ``matching.link.confirmed`` immediately.
- **Candidate generation (RAG)**: no GTIN → embed the product and find the nearest existing
  canonical by vector similarity (pgvector). Stage a ``pending_review`` link to the best
  match (if similar enough) or to a fresh draft canonical for an operator to confirm/reject.
  No event is emitted until confirmation.

All in one transaction; idempotent by event id.
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
    nearest_canonical,
)
from matching.domain.embedding import Embedder, HashingEmbedder, canonical_text
from matching.events.mapping import link_confirmed_record
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

# Minimum cosine similarity to suggest an existing canonical instead of proposing a new one.
CANDIDATE_THRESHOLD = 0.5


async def _gtin_auto_link(
    session: AsyncSession,
    product: SupplierProductDiscovered,
    gtin: str,
    embedding: list[float],
) -> None:
    canonical = await find_canonical_by_gtin(session, gtin)
    if canonical is None:
        canonical = create_canonical(
            session, gtin=gtin, brand=product.brand, title=product.name, embedding=embedding
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


async def _stage_candidate(
    session: AsyncSession, product: SupplierProductDiscovered, embedding: list[float]
) -> None:
    match = await nearest_canonical(session, embedding=embedding, brand=product.brand)
    if match is not None and match[1] >= CANDIDATE_THRESHOLD:
        canonical_product_id, confidence = match[0].canonical_product_id, match[1]
    else:
        draft = create_canonical(
            session,
            gtin=None,
            brand=product.brand,
            title=product.name,
            status="draft",
            embedding=embedding,
        )
        canonical_product_id, confidence = draft.canonical_product_id, (match[1] if match else 0.0)

    create_link(
        session,
        supplier_product_id=product.supplier_product_id,
        canonical_product_id=canonical_product_id,
        method="rag_suggested",
        confidence=max(0.0, confidence),
        status="pending_review",
        decided_by="system",
    )
    # no event yet — waits for an operator to confirm (see the curation API)


def build_discovered_handler(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    embedder: Embedder | None = None,
) -> EventHandler:
    """Build the ``supplier.product.discovered`` handler bound to a session factory.

    ``embedder`` defaults to the dependency-free :class:`HashingEmbedder`; production wires a
    real semantic model here.
    """
    embed = embedder or HashingEmbedder()

    async def handle(envelope: dict[str, Any]) -> None:
        event_id = envelope["id"]
        product = SupplierProductDiscovered(**envelope["data"])
        vector = embed.embed(canonical_text(product.name))
        async with session_factory() as session, session.begin():
            if await session.get(ProcessedEvent, event_id) is not None:
                return  # already handled
            session.add(ProcessedEvent(event_id=event_id))
            if await get_link(session, product.supplier_product_id) is not None:
                return  # already linked or queued

            if product.gtin is not None:
                await _gtin_auto_link(session, product, product.gtin, vector)
            else:
                await _stage_candidate(session, product, vector)

    return handle
