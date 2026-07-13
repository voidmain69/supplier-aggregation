"""Reciprocal Rank Fusion (pure domain — no I/O).

Hybrid search runs two independent retrievers — lexical (keyword AND-match) and semantic (vector
nearest-neighbour) — that score on incomparable scales. RRF merges their *ranked id lists* into one
order using only positions: a document's fused score is the sum over lists of ``1 / (k + rank)``.
It rewards documents that rank well in *either* retriever and needs no score normalisation.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

# Damping constant from the original RRF paper (Cormack et al., 2009). Larger k flattens the
# contribution of top ranks; 60 is the widely used default.
RRF_K = 60


def reciprocal_rank_fusion(
    rankings: Iterable[Sequence[str]], *, k: int = RRF_K
) -> list[tuple[str, float]]:
    """Fuse several ranked id lists into one ``(id, score)`` list, highest score first.

    ``rankings`` is one ranked sequence of document ids per retriever (rank 0 = best). Ids may
    repeat across lists (that is the point — agreement boosts the score) and each list may hold a
    different subset. Ties keep first-seen order, so the result is deterministic.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
