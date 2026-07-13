"""TeiReranker + NoopReranker + build_reranker — offline (httpx.MockTransport, no GPU/TEI)."""

from __future__ import annotations

import json

import httpx
from search.adapters.reranker import TeiReranker, build_reranker
from search.domain.rerank import NoopReranker


def test_build_reranker__no_url__is_noop() -> None:
    assert isinstance(build_reranker(None), NoopReranker)


def test_build_reranker__with_url__is_tei() -> None:
    assert isinstance(build_reranker("http://tei:80"), TeiReranker)


def test_noop_reranker__preserves_order_with_descending_scores() -> None:
    order = NoopReranker().rerank("q", ["a", "b", "c"])
    assert [i for i, _ in order] == [0, 1, 2]
    scores = [s for _, s in order]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 < s <= 1.0 for s in scores)


def test_noop_reranker__empty_documents() -> None:
    assert NoopReranker().rerank("q", []) == []


def test_tei_reranker__posts_query_and_texts_and_returns_sorted_pairs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rerank"
        body = json.loads(request.content)
        assert body["query"] == "gaming mouse"
        assert body["texts"] == ["motherboard", "gaming mouse pro", "keyboard"]
        return httpx.Response(
            200,
            json=[
                {"index": 1, "score": 0.98},
                {"index": 2, "score": 0.1},
                {"index": 0, "score": 0.001},
            ],
        )

    reranker = TeiReranker("http://tei:80", transport=httpx.MockTransport(handler))
    result = reranker.rerank("gaming mouse", ["motherboard", "gaming mouse pro", "keyboard"])
    assert result == [(1, 0.98), (2, 0.1), (0, 0.001)]


def test_tei_reranker__empty_documents_makes_no_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("TEI must not be called for an empty document set")

    reranker = TeiReranker("http://tei:80", transport=httpx.MockTransport(handler))
    assert reranker.rerank("q", []) == []
