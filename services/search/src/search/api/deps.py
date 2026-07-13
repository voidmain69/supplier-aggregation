"""FastAPI dependencies. Tests override ``get_session_factory`` with a SQLite factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from search.domain.embedding import Embedder
from search.domain.rerank import Reranker
from search.domain.sparse import SparseEmbedder


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return factory


def get_embedder(request: Request) -> Embedder:
    embedder: Embedder = request.app.state.embedder
    return embedder


def get_reranker(request: Request) -> Reranker:
    reranker: Reranker = request.app.state.reranker
    return reranker


def get_sparse_embedder(request: Request) -> SparseEmbedder | None:
    sparse_embedder: SparseEmbedder | None = request.app.state.sparse_embedder
    return sparse_embedder


async def get_session(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
