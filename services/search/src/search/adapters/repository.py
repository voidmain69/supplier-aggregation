"""Data access for the search index: upsert on ingest, lexical + exact-identifier lookups."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered
from sa_core.gtin import normalize_gtin
from sa_core.pagination import decode_cursor, encode_cursor
from search.adapters.models import SearchDocumentRow
from search.domain.embedding import cosine
from search.domain.query import document_text, tokenize

# PostgreSQL full-text config. "simple" (no stemming/stop-words) is language-agnostic — right for a
# multilingual product catalog where stemming would mangle brands/models across languages.
_FTS_CONFIG = "simple"


def _is_postgres(session: AsyncSession) -> bool:
    return session.bind is not None and session.bind.dialect.name == "postgresql"


def _pg_tsvector() -> ColumnElement[str]:
    return func.to_tsvector(_FTS_CONFIG, SearchDocumentRow.search_text)


def _lexical_condition(session: AsyncSession, query: str, tokens: list[str]) -> ColumnElement[bool]:
    """Lexical match predicate: PostgreSQL FTS (whole-lexeme, all terms) or portable LIKE (SQLite).

    FTS matches on word boundaries (so "cat" does not match "category"); the LIKE fallback is a
    substring AND, good enough for unit tests but coarser — see [ADR-0010].
    """
    if _is_postgres(session):
        return _pg_tsvector().op("@@")(func.plainto_tsquery(_FTS_CONFIG, query))
    return and_(*[SearchDocumentRow.search_text.like(f"%{token}%") for token in tokens])


async def index_document(
    session: AsyncSession,
    data: SupplierProductDiscovered,
    *,
    embedding: list[float] | None = None,
) -> None:
    """Insert or update the search document for a discovered supplier product (idempotent)."""
    gtin = normalize_gtin(data.gtin)
    text = document_text(data.name, data.brand, data.articul, data.external_code, data.external_id)
    row = await session.get(SearchDocumentRow, data.supplier_product_id)
    if row is None:
        session.add(
            SearchDocumentRow(
                supplier_product_id=data.supplier_product_id,
                supplier_code=data.supplier_code,
                external_id=data.external_id,
                external_code=data.external_code,
                articul=data.articul,
                gtin=gtin,
                name=data.name,
                brand=data.brand,
                search_text=text,
                embedding=embedding,
            )
        )
        return
    row.supplier_code = data.supplier_code
    row.external_id = data.external_id
    row.external_code = data.external_code
    row.articul = data.articul
    row.gtin = gtin
    row.name = data.name
    row.brand = data.brand
    row.search_text = text
    row.embedding = embedding


async def semantic_search(
    session: AsyncSession,
    embedding: list[float],
    *,
    limit: int = 20,
) -> list[tuple[SearchDocumentRow, float]]:
    """Nearest products to ``embedding`` by cosine similarity, most similar first.

    On Postgres this is a pgvector nearest-neighbour search (``<=>``); on SQLite (unit tests)
    it falls back to computing cosine in Python over the indexed set.
    """
    if _is_postgres(session):
        distance = SearchDocumentRow.embedding.cosine_distance(embedding)
        stmt = (
            select(SearchDocumentRow, distance.label("distance"))
            .where(SearchDocumentRow.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        return [(row, 1.0 - float(dist)) for row, dist in rows]

    # SQLite / other: score the candidate set in Python.
    stmt = select(SearchDocumentRow).where(SearchDocumentRow.embedding.is_not(None))
    scored = [
        (row, cosine(embedding, list(row.embedding or [])))
        for row in (await session.execute(stmt)).scalars().all()
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


async def search(
    session: AsyncSession,
    query: str,
    *,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[Sequence[SearchDocumentRow], str | None]:
    """Lexical search: all query terms must match a document (AND). Cursor-paged by id.

    On PostgreSQL this is a full-text match (whole lexemes, GIN-indexed); on SQLite it is a
    portable substring AND. Ordered by id (not relevance) so the cursor stays stable across pages;
    for relevance-ranked results use hybrid search. An empty query returns nothing.
    """
    tokens = tokenize(query)
    if not tokens:
        return [], None
    stmt = (
        select(SearchDocumentRow)
        .where(_lexical_condition(session, query, tokens))
        .order_by(SearchDocumentRow.supplier_product_id)
        .limit(limit)
    )
    if cursor is not None:
        stmt = stmt.where(
            SearchDocumentRow.supplier_product_id > str(decode_cursor(cursor)["after"])
        )
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = (
        encode_cursor({"after": rows[-1].supplier_product_id}) if len(rows) == limit else None
    )
    return rows, next_cursor


async def lexical_candidates(
    session: AsyncSession, query: str, *, limit: int = 50
) -> list[SearchDocumentRow]:
    """Lexical matches as a ranked candidate pool for hybrid fusion (no cursor).

    Same matching as :func:`search`, but on PostgreSQL the pool is ordered by FTS relevance
    (``ts_rank``) so the best lexical hits get the top RRF ranks; SQLite falls back to id order.
    An empty query (no usable tokens) returns nothing.
    """
    tokens = tokenize(query)
    if not tokens:
        return []
    stmt = select(SearchDocumentRow).where(_lexical_condition(session, query, tokens)).limit(limit)
    if _is_postgres(session):
        rank = func.ts_rank(_pg_tsvector(), func.plainto_tsquery(_FTS_CONFIG, query))
        stmt = stmt.order_by(rank.desc(), SearchDocumentRow.supplier_product_id)
    else:
        stmt = stmt.order_by(SearchDocumentRow.supplier_product_id)
    return list((await session.execute(stmt)).scalars().all())


async def find_by_code(session: AsyncSession, code: str) -> Sequence[SearchDocumentRow]:
    """Exact match on the supplier's product code (external_code) or external_id."""
    stmt = select(SearchDocumentRow).where(
        or_(
            SearchDocumentRow.external_code == code,
            SearchDocumentRow.external_id == code,
        )
    )
    return (await session.execute(stmt)).scalars().all()


async def find_by_articul(session: AsyncSession, articul: str) -> Sequence[SearchDocumentRow]:
    """Exact match on the supplier's articul."""
    stmt = select(SearchDocumentRow).where(SearchDocumentRow.articul == articul)
    return (await session.execute(stmt)).scalars().all()


async def find_by_gtin(session: AsyncSession, gtin: str) -> Sequence[SearchDocumentRow]:
    """Exact match on the normalized GTIN-14. Returns nothing if ``gtin`` is invalid."""
    normalized = normalize_gtin(gtin)
    if normalized is None:
        return []
    stmt = select(SearchDocumentRow).where(SearchDocumentRow.gtin == normalized)
    return (await session.execute(stmt)).scalars().all()
