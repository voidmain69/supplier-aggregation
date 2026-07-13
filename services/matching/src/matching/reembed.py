"""Re-embed every canonical product in place with the configured embedder.

Run with ``python -m matching.reembed`` (or ``make reembed svc=matching``). Needed after switching
or re-configuring the embedding model — e.g. the 256->1024 bge-m3 migration drops existing vectors,
so RAG candidate retrieval degrades until canonicals are re-embedded. Idempotent: processes rows in
id order in batches and can be safely re-run. Uses the same ``MATCHING_EMBEDDER_URL`` seam.
"""

from __future__ import annotations

import asyncio

import structlog
from sa_persistence.db import create_engine, create_session_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from matching.adapters.embedder import build_embedder
from matching.adapters.models import CanonicalProductRow
from matching.domain.embedding import Embedder, canonical_text
from matching.settings import Settings

log = structlog.get_logger(__name__)

_BATCH = 500


async def reembed_all(
    session_factory: async_sessionmaker[AsyncSession],
    embedder: Embedder,
    *,
    batch: int = _BATCH,
) -> int:
    """Recompute the embedding of every ``canonical_product`` row. Returns the count processed."""
    total = 0
    after: str | None = None
    while True:
        async with session_factory() as session, session.begin():
            stmt = (
                select(CanonicalProductRow)
                .order_by(CanonicalProductRow.canonical_product_id)
                .limit(batch)
            )
            if after is not None:
                stmt = stmt.where(CanonicalProductRow.canonical_product_id > after)
            rows = list((await session.execute(stmt)).scalars().all())
            if not rows:
                break
            for row in rows:
                row.embedding = embedder.embed(canonical_text(row.title))
            after = rows[-1].canonical_product_id
            total += len(rows)
        log.info("matching_reembed_batch", count=len(rows), total=total)
    return total


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    embedder = build_embedder(settings.embedder_url)
    total = await reembed_all(session_factory, embedder)
    log.info("matching_reembed_done", total=total, dim=embedder.dim)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
