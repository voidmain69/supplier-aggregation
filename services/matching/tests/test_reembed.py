"""Re-embed CLI: recompute every canonical product's embedding in place (SQLite)."""

from __future__ import annotations

from matching.adapters.models import CanonicalProductRow
from matching.reembed import reembed_all
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


async def test_reembed_all__rewrites_every_canonical_across_batches(
    sqlite_session_factory: SessionFactory,
) -> None:
    async with sqlite_session_factory() as session, session.begin():
        session.add_all(
            [
                CanonicalProductRow(
                    canonical_product_id="01J00000000000000000000001", title="thing one"
                ),
                CanonicalProductRow(
                    canonical_product_id="01J00000000000000000000002", title="thing two"
                ),
            ]
        )
    processed = await reembed_all(sqlite_session_factory, _FixedEmbedder(), batch=1)
    assert processed == 2

    async with sqlite_session_factory() as session:
        rows = (await session.execute(select(CanonicalProductRow))).scalars().all()
    assert rows
    assert all(list(row.embedding or []) == [0.5, 0.5, 0.5] for row in rows)


async def test_reembed_all__empty_is_zero(sqlite_session_factory: SessionFactory) -> None:
    assert await reembed_all(sqlite_session_factory, _FixedEmbedder()) == 0
