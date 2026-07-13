"""Production reranker: a Text-Embeddings-Inference (TEI) cross-encoder client.

Implements the domain :class:`~search.domain.rerank.Reranker` protocol against a TEI server's
``/rerank`` endpoint serving ``BAAI/bge-reranker-v2-m3`` (multilingual cross-encoder). Selected at
wiring time by ``SEARCH_RERANKER_URL``; when unset the service uses
:class:`~search.domain.rerank.NoopReranker`, so tests and offline runs need no GPU.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from search.domain.rerank import NoopReranker, Reranker

_RERANK_PATH = "/rerank"
_TIMEOUT_S = 30.0


class TeiReranker:
    """Reranks documents via a TEI server's ``/rerank`` endpoint (synchronous, pooled client).

    TEI scores every (query, text) pair with the cross-encoder and returns ``{index, score}``
    already sorted best-first, which is exactly the Reranker contract.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = _TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )

    def rerank(self, query: str, documents: Sequence[str]) -> list[tuple[int, float]]:
        if not documents:
            return []
        response = self._client.post(_RERANK_PATH, json={"query": query, "texts": list(documents)})
        response.raise_for_status()
        ranked = response.json()
        return [(int(item["index"]), float(item["score"])) for item in ranked]

    def close(self) -> None:
        self._client.close()


def build_reranker(url: str | None) -> Reranker:
    """Return the production TEI reranker when ``url`` is set, else the offline NoopReranker."""
    if url:
        return TeiReranker(url)
    return NoopReranker()
