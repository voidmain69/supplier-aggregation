"""Search API — lexical query + exact-identifier lookups (AI-ready, problem+json errors)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from sa_core.pagination import Page
from search.adapters.repository import (
    find_by_articul,
    find_by_code,
    find_by_gtin,
    lexical_candidates,
    search,
    semantic_search,
)
from search.api.deps import get_embedder, get_reranker, get_session
from search.api.schemas import (
    HybridSearchRequest,
    SearchHit,
    SearchRequest,
    SemanticSearchRequest,
)
from search.domain.embedding import Embedder, product_text
from search.domain.fusion import reciprocal_rank_fusion
from search.domain.rerank import Reranker

router = APIRouter(prefix="/v1", tags=["search"])


@router.post(
    "/search",
    operation_id="searchProducts",
    summary="Lexical product search",
    description=(
        "Search products by free text over name, brand, articul and codes. The query is "
        "tokenized and every token must match (AND). Cursor paginated. For exact identifiers "
        "prefer the by-code/by-articul/by-gtin lookups."
    ),
    response_model=Page[SearchHit],
)
async def search_products(
    body: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[SearchHit]:
    rows, next_cursor = await search(session, body.query, cursor=body.cursor, limit=body.limit)
    return Page(items=[SearchHit.from_row(r) for r in rows], next_cursor=next_cursor)


@router.post(
    "/search/semantic",
    operation_id="semanticSearch",
    summary="Semantic (natural-language) product search",
    description=(
        "Find products by meaning rather than keywords — describe the need in natural language "
        "('motherboard for Ryzen 9000 with Wi-Fi 7') and get the nearest products by embedding "
        "similarity. Each hit has a score in [0,1]. Use lexical search for keyword/code lookups."
    ),
    response_model=list[SearchHit],
)
async def search_semantic(
    body: SemanticSearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
) -> list[SearchHit]:
    vector = embedder.embed(body.query)
    hits = await semantic_search(session, vector, limit=body.limit)
    return [SearchHit.from_row(row, score=round(score, 4)) for row, score in hits]


@router.post(
    "/search/hybrid",
    operation_id="hybridSearch",
    summary="Hybrid product search (lexical + semantic, reranked)",
    description=(
        "Best-quality search: retrieves candidates both lexically (exact tokens) and semantically "
        "(embedding meaning), fuses them with Reciprocal Rank Fusion, then reorders with a "
        "cross-encoder reranker. Use this when you want the single best-ranked list and don't need "
        "pagination; each hit carries a relevance score. Prefer the by-code/articul/gtin lookups "
        "for exact identifiers."
    ),
    response_model=list[SearchHit],
)
async def search_hybrid(
    body: HybridSearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
) -> list[SearchHit]:
    vector = embedder.embed(body.query)
    lexical = await lexical_candidates(session, body.query, limit=body.pool)
    semantic = await semantic_search(session, vector, limit=body.pool)

    rows_by_id = {row.supplier_product_id: row for row in lexical}
    for row, _ in semantic:
        rows_by_id.setdefault(row.supplier_product_id, row)

    fused = reciprocal_rank_fusion(
        [
            [row.supplier_product_id for row in lexical],
            [row.supplier_product_id for row, _ in semantic],
        ]
    )
    candidates = [rows_by_id[cid] for cid, _ in fused[: body.pool]]
    if not candidates:
        return []

    texts = [product_text(row.name, row.brand) for row in candidates]
    ranked = reranker.rerank(body.query, texts)
    return [
        SearchHit.from_row(candidates[index], score=round(score, 4))
        for index, score in ranked[: body.limit]
    ]


@router.get(
    "/search/by-code/{code}",
    operation_id="searchByCode",
    summary="Find products by supplier code",
    description="Exact match on a supplier's product code (or external id). Returns all matches.",
    response_model=list[SearchHit],
)
async def by_code(
    code: Annotated[
        str, Path(description="Supplier product code or external id to match exactly.")
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SearchHit]:
    return [SearchHit.from_row(r) for r in await find_by_code(session, code)]


@router.get(
    "/search/by-articul/{articul}",
    operation_id="searchByArticul",
    summary="Find products by articul",
    description="Exact match on a supplier's articul. Returns all matches.",
    response_model=list[SearchHit],
)
async def by_articul(
    articul: Annotated[str, Path(description="Supplier articul to match exactly.")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SearchHit]:
    return [SearchHit.from_row(r) for r in await find_by_articul(session, articul)]


@router.get(
    "/search/by-gtin/{gtin}",
    operation_id="searchByGtin",
    summary="Find products by GTIN/EAN/UPC",
    description=(
        "Exact match on a GTIN/EAN/UPC. The value is normalized to GTIN-14 first; an invalid "
        "GTIN returns an empty list."
    ),
    response_model=list[SearchHit],
)
async def by_gtin(
    gtin: Annotated[str, Path(description="GTIN/EAN/UPC (normalized to GTIN-14 before matching).")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SearchHit]:
    return [SearchHit.from_row(r) for r in await find_by_gtin(session, gtin)]
