"""RAG candidate generation on Postgres via pgvector nearest-neighbour search. Integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from matching.adapters.models import CanonicalProductRow
from matching.adapters.repository import create_canonical, get_link
from matching.domain.embedding import HashingEmbedder, canonical_text
from matching.events.handlers import build_discovered_handler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]
_EMBEDDER = HashingEmbedder()


async def _seed(factory: SessionFactory, *, brand: str, title: str) -> str:
    async with factory() as session, session.begin():
        row = create_canonical(
            session,
            gtin=None,
            brand=brand,
            title=title,
            embedding=_EMBEDDER.embed(canonical_text(title)),
        )
        await session.flush()
        return row.canonical_product_id


async def test_pgvector_knn__links_to_the_nearest_canonical(
    pg_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    # Two same-brand canonicals; the incoming product matches the first.
    target = await _seed(pg_session_factory, brand="ASUS", title="ASUS TUF GAMING B850-PLUS WIFI")
    await _seed(pg_session_factory, brand="ASUS", title="ASUS ROG STRIX Z790 GAMING WIFI")

    handler = build_discovered_handler(pg_session_factory)
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD1",
            gtin=None,
            brand="ASUS",
            name="ASUS TUF GAMING B850-PLUS WIFI",
        )
    )

    async with pg_session_factory() as session:
        link = await get_link(session, "01J0000000000000000PROD1")
    assert link is not None
    assert link.status == "pending_review"
    assert link.method == "rag_suggested"
    assert link.canonical_product_id == target  # KNN picked the closest one
    assert link.confidence >= 0.5


async def test_pgvector_knn__no_close_match_creates_draft(
    pg_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    await _seed(pg_session_factory, brand="ASUS", title="ASUS ROG STRIX Z790 GAMING WIFI")

    handler = build_discovered_handler(pg_session_factory)
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD9",
            gtin=None,
            brand="ASUS",
            name="ASUS Prime H610M budget micro-ATX board",
        )
    )

    async with pg_session_factory() as session:
        link = await get_link(session, "01J0000000000000000PROD9")
        assert link is not None
        canonical = await session.get(CanonicalProductRow, link.canonical_product_id)
    assert canonical is not None
    assert canonical.status == "draft"  # below threshold -> new draft, not the Z790
