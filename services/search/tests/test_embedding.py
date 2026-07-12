"""Unit tests for the embedding domain (deterministic hashing embedder + cosine)."""

from __future__ import annotations

from search.domain.embedding import EMBEDDING_DIM, HashingEmbedder, cosine, product_text


def test_embed__is_deterministic_and_correct_dim() -> None:
    embedder = HashingEmbedder()
    a = embedder.embed("ASUS TUF B850")
    b = embedder.embed("ASUS TUF B850")
    assert len(a) == EMBEDDING_DIM
    assert a == b


def test_embed__is_l2_normalised() -> None:
    vec = HashingEmbedder().embed("some product name")
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_cosine__similar_text_scores_higher_than_unrelated() -> None:
    embedder = HashingEmbedder()
    query = embedder.embed("asus b850 motherboard wifi")
    close = embedder.embed("asus b850 plus wifi motherboard")
    far = embedder.embed("logitech wireless mouse")
    assert cosine(query, close) > cosine(query, far)


def test_cosine__degenerate_vector_is_zero() -> None:
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_product_text__joins_brand_and_name() -> None:
    assert product_text("TUF B850", "ASUS") == "ASUS TUF B850"
    assert product_text("TUF B850", None) == "TUF B850"
