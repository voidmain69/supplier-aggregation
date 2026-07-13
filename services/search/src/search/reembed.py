"""Re-embed every indexed document in place with the configured embedder.

Run with ``python -m search.reembed`` (or ``make reembed svc=search``). Needed after switching or
re-configuring the embedding model — e.g. the 256->1024 bge-m3 migration drops existing vectors, so
rows stay unsearchable-by-meaning until re-embedded. Idempotent: processes rows in id order in
batches and can be safely re-run. Uses the same ``SEARCH_EMBEDDER_URL`` seam as the live service.
"""

from __future__ import annotations

import asyncio

import structlog
from sa_persistence.db import create_engine, create_session_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from search.adapters.embedder import build_embedder
from search.adapters.models import SearchDocumentRow
from search.domain.embedding import Embedder, product_text
from search.settings import Settings

log = structlog.get_logger(__name__)

_BATCH = 500


async def reembed_all(
    session_factory: async_sessionmaker[AsyncSession],
    embedder: Embedder,
    *,
    batch: int = _BATCH,
) -> int:
    """Recompute the embedding of every ``search_document`` row. Returns the count processed."""
    total = 0
    after: str | None = None
    while True:
        async with session_factory() as session, session.begin():
            stmt = (
                select(SearchDocumentRow)
                .order_by(SearchDocumentRow.supplier_product_id)
                .limit(batch)
            )
            if after is not None:
                stmt = stmt.where(SearchDocumentRow.supplier_product_id > after)
            rows = list((await session.execute(stmt)).scalars().all())
            if not rows:
                break
            for row in rows:
                row.embedding = embedder.embed(product_text(row.name, row.brand))
            after = rows[-1].supplier_product_id
            total += len(rows)
        log.info("search_reembed_batch", count=len(rows), total=total)
    return total


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    embedder = build_embedder(settings.embedder_url)
    total = await reembed_all(session_factory, embedder)
    log.info("search_reembed_done", total=total, dim=embedder.dim)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
