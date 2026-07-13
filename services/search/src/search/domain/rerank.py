"""Cross-encoder reranking seam (protocol lives here; the real client is an adapter).

After lexical + semantic candidates are fused (see :mod:`search.domain.fusion`), a cross-encoder
rescoring the (query, document) pairs jointly gives far sharper relevance than either retriever
alone. :class:`Reranker` is the seam: production plugs a TEI ``bge-reranker`` client (adapters),
while :class:`NoopReranker` keeps the fused order so search runs with no reranker/GPU.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Reranker(Protocol):
    """Scores documents against a query and returns them ordered best-first."""

    def rerank(self, query: str, documents: Sequence[str]) -> list[tuple[int, float]]:
        """Return ``(index_into_documents, score)`` pairs, highest score first."""
        ...


class NoopReranker:
    """Identity reranker: preserves the input (fused) order, so search works without a GPU.

    Scores are positional placeholders in ``(0, 1]`` (monotonically decreasing) — meaningful as an
    order, not as calibrated relevance. Production wires ``TeiReranker`` for real cross-encoder
    scores.
    """

    def rerank(self, query: str, documents: Sequence[str]) -> list[tuple[int, float]]:
        n = len(documents)
        return [(i, (n - i) / n) for i in range(n)]
