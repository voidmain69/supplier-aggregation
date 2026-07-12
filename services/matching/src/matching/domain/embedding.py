"""Embeddings for candidate retrieval (pure domain — no I/O).

Matching finds candidate canonicals by nearest-neighbour search over embedding vectors
(pgvector) instead of a lexical scan. The :class:`Embedder` protocol is the seam: production
plugs in a real semantic model (e.g. a Voyage/sentence-transformers client), while the
default :class:`HashingEmbedder` is deterministic and dependency-free — enough to exercise
the whole vector path and keep tests reproducible.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

# Fixed at the DB column width (Vector(EMBEDDING_DIM)); changing it is a migration.
EMBEDDING_DIM = 256

_TOKEN = re.compile(r"[^a-z0-9]+")


def canonical_text(name: str) -> str:
    """The text embedded for a product. Brand is a hard filter on the search, not embedded,
    so same-brand products are compared by name (their distinguishing identity)."""
    return name.strip()


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN.split(text.lower()) if token]


class Embedder(Protocol):
    """Turns product text into a fixed-length embedding vector."""

    @property
    def dim(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Deterministic feature-hashing embedder (bag-of-tokens in vector space, L2-normalised).

    Not a learned semantic model — a dependency-free default so the pgvector path works out of
    the box and tests stay reproducible. Swap a real model in via the :class:`Embedder` protocol.
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for token in _tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if digest[4] & 1 else -1.0  # signed hashing reduces collisions
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors in [-1, 1] (0 if either is degenerate)."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
