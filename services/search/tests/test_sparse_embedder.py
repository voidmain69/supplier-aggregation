"""TeiSparseEmbedder + build_sparse_embedder — offline (httpx.MockTransport, no GPU/TEI)."""

from __future__ import annotations

import json

import httpx
from search.adapters.sparse_embedder import TeiSparseEmbedder, build_sparse_embedder


def test_build_sparse_embedder__no_url__is_none() -> None:
    assert build_sparse_embedder(None) is None


def test_build_sparse_embedder__with_url__is_tei() -> None:
    assert isinstance(build_sparse_embedder("http://tei:80"), TeiSparseEmbedder)


def test_tei_sparse_embedder__unwraps_batch_into_id_weight_map() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/embed_sparse"
        body = json.loads(request.content)
        assert body["inputs"] == ["wireless mouse"]
        return httpx.Response(
            200, json=[[{"index": 1059, "value": 0.49}, {"index": 2003, "value": 0.29}]]
        )

    embedder = TeiSparseEmbedder("http://tei:80", transport=httpx.MockTransport(handler))
    assert embedder.embed_sparse("wireless mouse") == {1059: 0.49, 2003: 0.29}


def test_tei_sparse_embedder__server_error_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "overloaded"})

    embedder = TeiSparseEmbedder("http://tei:80", transport=httpx.MockTransport(handler))
    try:
        embedder.embed_sparse("x")
    except httpx.HTTPStatusError:
        return
    raise AssertionError("expected HTTPStatusError on 503")
