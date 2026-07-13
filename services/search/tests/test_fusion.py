"""Reciprocal Rank Fusion — pure domain, no I/O."""

from __future__ import annotations

from search.domain.fusion import reciprocal_rank_fusion


def test_rrf__agreement_across_lists_outranks_single_list_top() -> None:
    # "a" is present in both retrievers; "b"/"c" each in only one.
    fused = reciprocal_rank_fusion([["a", "b"], ["a", "c"]])
    ids = [key for key, _ in fused]
    assert ids[0] == "a"
    assert set(ids) == {"a", "b", "c"}


def test_rrf__respects_rank_within_a_list() -> None:
    scores = dict(reciprocal_rank_fusion([["x", "y", "z"]]))
    assert scores["x"] > scores["y"] > scores["z"]


def test_rrf__larger_k_flattens_top_rank_weight() -> None:
    small_k = dict(reciprocal_rank_fusion([["a"]], k=1))
    large_k = dict(reciprocal_rank_fusion([["a"]], k=1000))
    assert small_k["a"] > large_k["a"]


def test_rrf__empty_inputs_yield_empty() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
