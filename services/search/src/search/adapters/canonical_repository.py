"""Data access for the canonical-product search index (``catalog.product.updated`` projection).

Mirrors the supplier-product retrieval in :mod:`search.adapters.repository` but over
``canonical_document`` — lexical (FTS / LIKE), dense semantic (pgvector / Python) and learned-sparse
(SPLADE), so hybrid search can return canonical product ids.
"""

from __future__ import annotations

from pgvector import SparseVector
from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sa_contracts.events.catalog_product_updated import CatalogProductUpdated
from sa_core.gtin import normalize_gtin
from search.adapters.models import CanonicalDocumentRow
from search.domain.embedding import cosine
from search.domain.query import document_text, tokenize
from search.domain.sparse import SPARSE_DIM

_FTS_CONFIG = "simple"


def _is_postgres(session: AsyncSession) -> bool:
    return session.bind is not None and session.bind.dialect.name == "postgresql"


def _lexical_condition(session: AsyncSession, query: str, tokens: list[str]) -> ColumnElement[bool]:
    if _is_postgres(session):
        tsv = func.to_tsvector(_FTS_CONFIG, CanonicalDocumentRow.search_text)
        return tsv.op("@@")(func.plainto_tsquery(_FTS_CONFIG, query))
    return and_(*[CanonicalDocumentRow.search_text.like(f"%{token}%") for token in tokens])


async def index_canonical_document(
    session: AsyncSession,
    data: CatalogProductUpdated,
    *,
    embedding: list[float] | None = None,
    sparse: dict[int, float] | None = None,
) -> None:
    """Insert or update the search document for a canonical product card (idempotent)."""
    gtin = normalize_gtin(data.gtin)
    text = document_text(data.title, data.brand, gtin)
    sparse_vec = SparseVector(sparse, SPARSE_DIM) if sparse else None
    row = await session.get(CanonicalDocumentRow, data.canonical_product_id)
    if row is None:
        session.add(
            CanonicalDocumentRow(
                canonical_product_id=data.canonical_product_id,
                gtin=gtin,
                title=data.title,
                brand=data.brand,
                search_text=text,
                embedding=embedding,
                embedding_sparse=sparse_vec,
            )
        )
        return
    row.gtin = gtin
    row.title = data.title
    row.brand = data.brand
    row.search_text = text
    row.embedding = embedding
    row.embedding_sparse = sparse_vec


async def canonical_lexical_candidates(
    session: AsyncSession, query: str, *, limit: int = 50
) -> list[CanonicalDocumentRow]:
    """Lexical candidate pool for hybrid fusion (FTS ts_rank on Postgres, LIKE on SQLite)."""
    tokens = tokenize(query)
    if not tokens:
        return []
    stmt = (
        select(CanonicalDocumentRow).where(_lexical_condition(session, query, tokens)).limit(limit)
    )
    if _is_postgres(session):
        tsv = func.to_tsvector(_FTS_CONFIG, CanonicalDocumentRow.search_text)
        rank = func.ts_rank(tsv, func.plainto_tsquery(_FTS_CONFIG, query))
        stmt = stmt.order_by(rank.desc(), CanonicalDocumentRow.canonical_product_id)
    else:
        stmt = stmt.order_by(CanonicalDocumentRow.canonical_product_id)
    return list((await session.execute(stmt)).scalars().all())


async def canonical_semantic_search(
    session: AsyncSession, embedding: list[float], *, limit: int = 20
) -> list[tuple[CanonicalDocumentRow, float]]:
    """Nearest canonical documents by cosine similarity (pgvector on Postgres, Python on SQLite)."""
    if _is_postgres(session):
        distance = CanonicalDocumentRow.embedding.cosine_distance(embedding)
        stmt = (
            select(CanonicalDocumentRow, distance.label("distance"))
            .where(CanonicalDocumentRow.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        return [(row, 1.0 - float(dist)) for row, dist in rows]

    stmt = select(CanonicalDocumentRow).where(CanonicalDocumentRow.embedding.is_not(None))
    scored = [
        (row, cosine(embedding, list(row.embedding or [])))
        for row in (await session.execute(stmt)).scalars().all()
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


async def canonical_sparse_candidates(
    session: AsyncSession, sparse_query: dict[int, float], *, limit: int = 50
) -> list[CanonicalDocumentRow]:
    """SPLADE candidate pool by max inner product (PostgreSQL only; other dialects -> [])."""
    if not sparse_query or not _is_postgres(session):
        return []
    query_vec = SparseVector(sparse_query, SPARSE_DIM)
    distance = CanonicalDocumentRow.embedding_sparse.max_inner_product(query_vec)
    stmt = (
        select(CanonicalDocumentRow)
        .where(CanonicalDocumentRow.embedding_sparse.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
