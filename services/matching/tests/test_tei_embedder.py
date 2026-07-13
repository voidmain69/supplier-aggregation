"""TeiEmbedder + build_embedder — offline (httpx.MockTransport, no GPU/TEI needed)."""

from __future__ import annotations

import json

import httpx
from matching.adapters.embedder import TeiEmbedder, build_embedder
from matching.domain.embedding import EMBEDDING_DIM, HashingEmbedder


def test_build_embedder__no_url__is_offline_hashing_embedder() -> None:
    embedder = build_embedder(None)
    assert isinstance(embedder, HashingEmbedder)
    assert embedder.dim == EMBEDDING_DIM


def test_build_embedder__with_url__is_tei_embedder() -> None:
    embedder = build_embedder("http://tei:80")
    assert isinstance(embedder, TeiEmbedder)
    assert embedder.dim == EMBEDDING_DIM


def test_tei_embedder__posts_batch_of_one_and_unwraps_vector() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/embed"
        body = json.loads(request.content)
        assert body["inputs"] == ["battery 12V"]
        assert body["normalize"] is True
        return httpx.Response(200, json=[[0.1, 0.2, 0.3, 0.4]])

    embedder = TeiEmbedder("http://tei:80", dim=4, transport=httpx.MockTransport(handler))
    assert embedder.embed("battery 12V") == [0.1, 0.2, 0.3, 0.4]


def test_tei_embedder__server_error_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "overloaded"})

    embedder = TeiEmbedder("http://tei:80", transport=httpx.MockTransport(handler))
    try:
        embedder.embed("x")
    except httpx.HTTPStatusError:
        return
    raise AssertionError("expected HTTPStatusError on 503")
