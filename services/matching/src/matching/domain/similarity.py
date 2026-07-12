"""Lexical similarity for candidate generation (no I/O).

A deliberately simple, deterministic scorer: token-overlap (Jaccard) of the names, with a
brand boost/penalty. It is the pluggable step that a semantic pgvector/RAG scorer will
replace later — the curation workflow around it stays the same.
"""

from __future__ import annotations

import re

_SEP = re.compile(r"[^a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {token for token in _SEP.split(text.lower()) if token}


def similarity(name_a: str, brand_a: str | None, name_b: str, brand_b: str | None) -> float:
    """Score two products in [0, 1]. Higher = more likely the same product."""
    tokens_a, tokens_b = _tokens(name_a), _tokens(name_b)
    if not tokens_a or not tokens_b:
        return 0.0
    jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    if brand_a and brand_b:
        if brand_a.lower() == brand_b.lower():
            return min(1.0, jaccard + 0.1)  # small boost when brands agree
        return jaccard * 0.5  # penalty when brands clearly differ
    return jaccard
