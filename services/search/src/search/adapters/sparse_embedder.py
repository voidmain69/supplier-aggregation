"""Production sparse embedder: a Text-Embeddings-Inference (TEI) SPLADE client.

Implements the domain :class:`~search.domain.sparse.SparseEmbedder` protocol against a TEI server's
``/embed_sparse`` endpoint serving ``naver/splade-v3-distilbert``. Selected at wiring time by
``SEARCH_SPARSE_EMBEDDER_URL``; when unset ``build_sparse_embedder`` returns ``None`` and hybrid
search simply omits the sparse retriever — so tests and offline runs need no GPU.
"""

from __future__ import annotations

import httpx

from search.domain.sparse import SparseEmbedder

_EMBED_SPARSE_PATH = "/embed_sparse"
_TIMEOUT_S = 30.0


class TeiSparseEmbedder:
    """Sparse-embeds text via a TEI server's ``/embed_sparse`` endpoint (synchronous client).

    TEI returns a batch of sparse vectors, each a list of ``{index, value}`` pairs (0-based token
    ids); we send one text and unwrap the single vector into a ``{id: weight}`` map.
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

    def embed_sparse(self, text: str) -> dict[int, float]:
        response = self._client.post(_EMBED_SPARSE_PATH, json={"inputs": [text], "truncate": True})
        response.raise_for_status()
        vectors = response.json()
        return {int(pair["index"]): float(pair["value"]) for pair in vectors[0]}

    def close(self) -> None:
        self._client.close()


def build_sparse_embedder(url: str | None) -> SparseEmbedder | None:
    """Return the TEI sparse embedder when ``url`` is set, else ``None`` (sparse retrieval off)."""
    if url:
        return TeiSparseEmbedder(url)
    return None
