from __future__ import annotations

from collections.abc import Callable
from typing import Any

from matching.adapters.models import CanonicalProductRow
from matching.adapters.repository import create_canonical, get_link
from matching.domain.embedding import HashingEmbedder, canonical_text
from matching.events.handlers import build_discovered_handler
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]
_EMBEDDER = HashingEmbedder()


async def _seed_canonical(factory: SessionFactory, *, brand: str, title: str) -> str:
    async with factory() as session, session.begin():
        row = create_canonical(
            session,
            gtin=None,
            brand=brand,
            title=title,
            status="confirmed",
            embedding=_EMBEDDER.embed(canonical_text(title)),
        )
        await session.flush()
        return row.canonical_product_id


async def _canonical_count(factory: SessionFactory) -> int:
    async with factory() as session:
        return int(
            (
                await session.execute(select(func.count()).select_from(CanonicalProductRow))
            ).scalar_one()
        )


async def test_no_gtin__similar_canonical__pending_link_to_it(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    canonical_id = await _seed_canonical(
        sqlite_session_factory, brand="ASUS", title="ASUS TUF GAMING B850-PLUS WIFI"
    )
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD1",
            gtin=None,
            brand="ASUS",
            name="ASUS TUF GAMING B850-PLUS WIFI",
        )
    )

    async with sqlite_session_factory() as session:
        link = await get_link(session, "01J0000000000000000PROD1")
    assert link is not None
    assert link.status == "pending_review"
    assert link.method == "rag_suggested"
    assert link.canonical_product_id == canonical_id  # matched the existing one, no draft
    assert await _canonical_count(sqlite_session_factory) == 1
    # nothing emitted until an operator confirms
    assert await OutboxRelay(sqlite_session_factory, InMemoryPublisher()).drain() == 0


async def test_no_gtin__no_match__creates_draft_and_pending_link(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD1",
            gtin=None,
            brand="ASUS",
            name="Completely unrelated widget xyz",
        )
    )

    async with sqlite_session_factory() as session:
        link = await get_link(session, "01J0000000000000000PROD1")
        assert link is not None
        draft = await session.get(CanonicalProductRow, link.canonical_product_id)
    assert link.status == "pending_review"
    assert draft is not None
    assert draft.status == "draft"


async def test_no_gtin__dissimilar_existing__still_drafts(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    await _seed_canonical(sqlite_session_factory, brand="ASUS", title="ASUS ROG STRIX Z790")
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD1",
            gtin=None,
            brand="ASUS",
            name="ASUS Prime H610M budget board",
        )
    )

    async with sqlite_session_factory() as session:
        link = await get_link(session, "01J0000000000000000PROD1")
        assert link is not None
        canonical = await session.get(CanonicalProductRow, link.canonical_product_id)
    assert canonical is not None
    assert canonical.status == "draft"  # below threshold -> new draft, not the Z790
