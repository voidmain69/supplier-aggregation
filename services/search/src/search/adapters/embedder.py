"""Production embedder: a Text-Embeddings-Inference (TEI) HTTP client.

The domain defines the :class:`~search.domain.embedding.Embedder` protocol; this adapter
implements it against a TEI server (github.com/huggingface/text-embeddings-inference) serving
``BAAI/bge-m3`` (1024-dim, multilingual, CLS pooling). It is selected at wiring time by
``SEARCH_EMBEDDER_URL``: when that is unset the service falls back to the dependency-free
:class:`~search.domain.embedding.HashingEmbedder`, so tests and offline runs need no GPU. Both
embedders emit ``dim``-wide vectors, so the pgvector column width is identical either way.
"""

from __future__ import annotations

import httpx

from search.domain.embedding import EMBEDDING_DIM, Embedder, HashingEmbedder

_EMBED_PATH = "/embed"
_TIMEOUT_S = 30.0


class TeiEmbedder:
    """Embeds text via a TEI server's ``/embed`` endpoint (synchronous, pooled client).

    Kept synchronous to satisfy the Embedder protocol; a bge-m3 call on a local GPU is a few
    milliseconds. Vectors are L2-normalised by the server (``normalize=true``) so cosine distance
    in pgvector is meaningful. TEI accepts a batch, so we send a single-element list and unwrap it.
    """

    def __init__(
        self,
        base_url: str,
        *,
        dim: int = EMBEDDING_DIM,
        timeout: float = _TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._dim = dim
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        response = self._client.post(
            _EMBED_PATH, json={"inputs": [text], "normalize": True, "truncate": True}
        )
        response.raise_for_status()
        vectors = response.json()
        return [float(x) for x in vectors[0]]

    def close(self) -> None:
        self._client.close()


def build_embedder(url: str | None, *, dim: int = EMBEDDING_DIM) -> Embedder:
    """Return the production TEI embedder when ``url`` is set, else the offline HashingEmbedder.

    This is the single seam that swaps the real semantic model in for the deterministic stand-in.
    """
    if url:
        return TeiEmbedder(url, dim=dim)
    return HashingEmbedder(dim=dim)
