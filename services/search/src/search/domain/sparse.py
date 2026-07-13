"""Learned-sparse retrieval seam (protocol lives here; the TEI client is an adapter).

A SPLADE model expands text into a sparse vocabulary vector — a few hundred weighted term ids
(``{token_id: weight}``) — which retrieves by learned lexical importance, catching exact-term and
expansion matches that dense embeddings blur. It is a third, complementary retriever fused with
lexical + dense in hybrid search. :class:`SparseEmbedder` is the seam; the production client
(``TeiSparseEmbedder``) is opt-in, so sparse retrieval is skipped entirely when unconfigured.
"""

from __future__ import annotations

from typing import Protocol

# Vocabulary width of naver/splade-v3-distilbert — the sparsevec column dimension. Token ids are
# 0-based (as returned by TEI) and stored as such; pgvector's SparseVector handles the mapping.
SPARSE_DIM = 30522


class SparseEmbedder(Protocol):
    """Expands text into a sparse ``{token_id: weight}`` vector (0-based ids)."""

    def embed_sparse(self, text: str) -> dict[int, float]: ...
