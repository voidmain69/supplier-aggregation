"""Re-embed CLI: recompute every document's embedding in place (SQLite)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from search.adapters.models import SearchDocumentRow
from search.events.handlers import build_discovered_handler
from search.reembed import reembed_all
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


class _FixedEmbedder:
    """Stub embedder returning a constant vector, to prove rows are rewritten."""

    @property
    def dim(self) -> int:
        return 3

    def embed(self, text: str) -> list[float]:
        return [0.5, 0.5, 0.5]


async def _seed(factory: SessionFactory, events: list[dict[str, Any]]) -> None:
    handler = build_discovered_handler(factory)
    for event in events:
        await handler(event)


async def test_reembed_all__rewrites_every_row_across_batches(
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        [
            discovered_event(supplier_product_id="01J00000000000000000000001", name="a", gtin=None),
            discovered_event(supplier_product_id="01J00000000000000000000002", name="b", gtin=None),
        ],
    )
    processed = await reembed_all(sqlite_session_factory, _FixedEmbedder(), batch=1)
    assert processed == 2

    async with sqlite_session_factory() as session:
        rows = (await session.execute(select(SearchDocumentRow))).scalars().all()
    assert rows
    assert all(list(row.embedding or []) == [0.5, 0.5, 0.5] for row in rows)


async def test_reembed_all__empty_index_processes_nothing(
    sqlite_session_factory: SessionFactory,
) -> None:
    assert await reembed_all(sqlite_session_factory, _FixedEmbedder()) == 0
