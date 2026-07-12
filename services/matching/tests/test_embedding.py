"""The default hashing embedder and cosine helper (pure, no DB)."""

from __future__ import annotations

import math

from matching.domain.embedding import EMBEDDING_DIM, HashingEmbedder, canonical_text, cosine


def test_embed__is_deterministic_and_unit_length() -> None:
    embedder = HashingEmbedder()
    a = embedder.embed("ASUS TUF GAMING B850-PLUS WIFI")
    b = embedder.embed("ASUS TUF GAMING B850-PLUS WIFI")
    assert a == b
    assert len(a) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-9)


def test_embed__empty_text_is_zero_vector() -> None:
    assert cosine(HashingEmbedder().embed(""), HashingEmbedder().embed("anything")) == 0.0


def test_cosine__identical_text_is_one() -> None:
    embedder = HashingEmbedder()
    vec = embedder.embed("ASUS TUF GAMING B850-PLUS WIFI")
    assert math.isclose(cosine(vec, vec), 1.0, rel_tol=1e-9)


def test_cosine__same_product_beats_different_product() -> None:
    embedder = HashingEmbedder()
    query = embedder.embed(canonical_text("ASUS TUF GAMING B850-PLUS WIFI"))
    same = embedder.embed(canonical_text("ASUS TUF GAMING B850-PLUS WIFI"))
    other = embedder.embed(canonical_text("ASUS ROG STRIX Z790 gaming"))
    assert cosine(query, same) > cosine(query, other)
    assert cosine(query, other) < 0.5  # clearly a different product


def test_cosine__is_bounded() -> None:
    embedder = HashingEmbedder()
    a = embedder.embed("intel core i9 14900k")
    b = embedder.embed("amd ryzen 9 7950x")
    assert -1.0 <= cosine(a, b) <= 1.0
