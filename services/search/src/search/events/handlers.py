"""Event handler: index a supplier product on discovery (idempotent, with its embedding)."""

from __future__ import annotations

from typing import Any

from sa_messaging import EventHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered
from search.adapters.models import ProcessedEvent
from search.adapters.repository import index_document
from search.domain.embedding import Embedder, HashingEmbedder, product_text
from search.domain.sparse import SparseEmbedder


def build_discovered_handler(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    embedder: Embedder | None = None,
    sparse_embedder: SparseEmbedder | None = None,
) -> EventHandler:
    """Build a handler for ``supplier.product.discovered`` bound to a session factory.

    ``embedder`` defaults to the dependency-free :class:`HashingEmbedder`; production wires a
    real semantic model here. ``sparse_embedder`` is optional — when set, each document is also
    SPLADE-embedded for the hybrid sparse retriever.
    """
    embed = embedder or HashingEmbedder()

    async def handle(envelope: dict[str, Any]) -> None:
        event_id = envelope["id"]
        payload = SupplierProductDiscovered(**envelope["data"])
        text = product_text(payload.name, payload.brand)
        vector = embed.embed(text)
        sparse = sparse_embedder.embed_sparse(text) if sparse_embedder is not None else None
        async with session_factory() as session, session.begin():
            if await session.get(ProcessedEvent, event_id) is not None:
                return  # already indexed — idempotent skip
            await index_document(session, payload, embedding=vector, sparse=sparse)
            session.add(ProcessedEvent(event_id=event_id))

    return handle
